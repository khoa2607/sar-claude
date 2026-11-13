"""Coordinate mapping tests. Expected values come from geometry, not from the code under test."""
from pathlib import Path

import numpy as np
import pytest

import sarkit.wgs84 as wgs84

from sarsil.geometry.sicd_coords import SicdGeometry

ROOT = Path(__file__).resolve().parents[1] / "cphd"
SICD = ROOT / "2023-11-19-16-12-16_UMBRA-05_SICD.nitf"
CPHD = ROOT / "2023-11-19-16-12-16_UMBRA-05_CPHD.cphd"
pytestmark = [pytest.mark.realdata, pytest.mark.skipif(not SICD.exists(), reason="local SICD not present")]


@pytest.fixture(scope="module")
def geo():
    return SicdGeometry.from_sicd(SICD)


def test_basic_geometry_values(geo):
    assert (geo.num_rows, geo.num_cols) == (5045, 5345)
    assert (geo.scp_pixel_row, geo.scp_pixel_col) == (2513, 2667)
    assert geo.scp_ecf == pytest.approx([-552223.3276367188, -4332875.0, 4632556.640625])


def test_unit_vectors_are_orthonormal(geo):
    assert np.linalg.norm(geo.row_uvect) == pytest.approx(1.0, abs=1e-8)
    assert np.linalg.norm(geo.col_uvect) == pytest.approx(1.0, abs=1e-8)
    assert geo.row_uvect @ geo.col_uvect == pytest.approx(0.0, abs=1e-8)


def test_scp_pixel_maps_to_scp(geo):
    scp_px = [geo.scp_pixel_row, geo.scp_pixel_col]
    assert geo.pixel_to_ecf_slant(scp_px) == pytest.approx(geo.scp_ecf, abs=1e-6)
    assert geo.pixel_to_ecf_ground(scp_px) == pytest.approx(geo.scp_ecf, abs=1e-3)


def test_one_pixel_moves_exactly_one_sample_spacing_along_the_matching_axis(geo):
    r0, c0 = geo.scp_pixel_row, geo.scp_pixel_col
    d_row = geo.pixel_to_ecf_slant([r0 + 1, c0]) - geo.scp_ecf
    d_col = geo.pixel_to_ecf_slant([r0, c0 + 1]) - geo.scp_ecf
    assert d_row == pytest.approx(geo.row_ss * geo.row_uvect, abs=1e-9)
    assert d_col == pytest.approx(geo.col_ss * geo.col_uvect, abs=1e-9)
    # axes are not transposed: row displacement has no component along the column axis and vice versa
    assert abs(d_row @ geo.col_uvect) < 1e-6 and abs(d_col @ geo.row_uvect) < 1e-6


def test_plane_meters_and_pixels_round_trip(geo):
    px = np.array([[0, 0], [5044, 5344], [100, 4000], [2513, 2667]], dtype=float)
    assert geo.plane_m_to_pixel(geo.pixel_to_plane_m(px)) == pytest.approx(px, abs=1e-9)
    assert geo.pixel_to_plane_m([geo.scp_pixel_row, geo.scp_pixel_col]) == pytest.approx([0.0, 0.0], abs=1e-12)


def test_slant_plane_round_trip_in_plane(geo):
    px = np.array([[10.0, 20.0], [3000.5, 4000.25]])
    ecf = geo.pixel_to_ecf_slant(px)
    # 1e-4 m: the file's unit vectors are unit/orthogonal only to about 3e-10, which limits the round trip to ~1e-6 m
    assert geo.ecf_to_plane_m_slant(ecf) == pytest.approx(geo.pixel_to_plane_m(px), abs=1e-4)


def test_ground_projection_lies_on_the_local_horizontal_plane(geo):
    px = np.array([[0.0, 0.0], [5044.0, 5344.0], [2513.0, 100.0]])
    gp = geo.pixel_to_ecf_ground(px)
    up = wgs84.up(wgs84.cartesian_to_geodetic(geo.scp_ecf))
    assert (gp - geo.scp_ecf) @ up == pytest.approx([0, 0, 0], abs=1e-3)


def test_ground_round_trip_pixel_ecf_pixel(geo):
    rng = np.random.default_rng(7)
    px = np.column_stack([rng.uniform(0, 5044, 20), rng.uniform(0, 5344, 20)])
    px = np.vstack([px, [[0, 0], [0, 5344], [5044, 5344], [5044, 0]]])
    back = geo.ecf_to_pixel(geo.pixel_to_ecf_ground(px))
    # 0.01 pixel: SARkit's scene-to-image stops when the ground-plane displacement is below 1 mm (about 0.002 pixel)
    assert back == pytest.approx(px, abs=0.01)


def test_range_foreshortening_matches_graze_angle(geo):
    # Moving 100 slant-range meters changes the flat-ground distance by about 1/cos(graze angle).
    graze = np.radians(53.89328163094831)                 # SICD SCPCOA/GrazeAng
    r0, c0 = geo.scp_pixel_row, geo.scp_pixel_col
    n = 100.0 / geo.row_ss
    g = geo.pixel_to_ecf_ground([r0 + n, c0]) - geo.pixel_to_ecf_ground([r0, c0])
    assert np.linalg.norm(g) / 100.0 == pytest.approx(1 / np.cos(graze), rel=0.01)
    # azimuth direction is almost unaffected (Doppler cone near 90 degrees)
    n = 100.0 / geo.col_ss
    a = geo.pixel_to_ecf_ground([r0, c0 + n]) - geo.pixel_to_ecf_ground([r0, c0])
    assert np.linalg.norm(a) / 100.0 == pytest.approx(1.0, rel=0.01)


def test_corner_pixels_map_to_the_matching_declared_corner_not_a_transposed_one(geo):
    # SICD GeoData/ImageCorners order: FRFC, FRLC, LRLC, LRFC (first/last row, first/last column).
    px = [[0, 0], [0, geo.num_cols - 1], [geo.num_rows - 1, geo.num_cols - 1], [geo.num_rows - 1, 0]]
    llh = wgs84.cartesian_to_geodetic(geo.pixel_to_ecf_hae(px, hae_m=geo.scp_llh[2]))
    mine = wgs84.geodetic_to_cartesian(np.column_stack([llh[:, :2], np.zeros(4)]))
    decl = wgs84.geodetic_to_cartesian(np.column_stack([geo.declared_image_corners_lat_lon, np.zeros(4)]))
    dist = np.linalg.norm(mine[:, None] - decl[None], axis=2)
    assert (dist.argmin(axis=1) == np.arange(4)).all()                  # orientation and ordering are right
    assert dist[~np.eye(4, dtype=bool)].min() > 4000.0                  # wrong pairings are kilometers away
    # Regression bound, NOT an accuracy claim: the matching corners differ by about 15 m (observed 13-15 m).
    # How the producer computed ImageCorners is undocumented (see docs/M2_SICD_REFERENCE.md).
    assert np.diag(dist).max() < 20.0


def test_cphd_iac_agrees_with_sicd_ground_plane(geo):
    import sarkit.cphd as sc
    with open(CPHD, "rb") as f:
        cx = sc.Reader(f).metadata.xmltree
    assert geo.ecf_to_cphd_iac(cx, geo.scp_ecf) == pytest.approx([0, 0, 0], abs=1e-3)
    # both planes are the horizontal plane at the SCP, so ground-projected pixels have IAC z ~ 0
    gp = geo.pixel_to_ecf_ground([[0, 0], [5044, 5344], [2513, 100]])
    assert np.abs(geo.ecf_to_cphd_iac(cx, gp)[:, 2]).max() < 0.01
