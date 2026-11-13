"""Minimum coordinate mapping between SICD image pixels, image planes, ECF and CPHD image-area coordinates.

Conventions (all taken from SICD / CPHD, implemented through SARkit; nothing here is a new algorithm):

* Pixel (row, col): global zero-based indices into the full SICD image (SICD ImageData); integer values are pixel centers.
* Image plane coordinates (xrow, ycol): meters, origin at the SCP pixel, xrow along Grid/Row/UVectECF scaled by Row/SS,
  ycol along Grid/Col/UVectECF scaled by Col/SS. This is the SICD *slant* plane for this product (Grid/ImagePlane = SLANT).
* ECF: WGS 84 Earth-centered Earth-fixed Cartesian, meters.
* Ground plane: the plane through a reference point (default the SCP) with a given unit normal (default the geodetic
  "up" at the SCP). A pixel is projected onto it along the radar's range/Doppler contours (SICD Volume 3), not by
  simple orthogonal projection.
* CPHD IAC: image-area coordinates (meters) of the CPHD scene (SceneCoordinates), converted with SARkit.

Array arguments have a trailing axis of length 2 (pixels, plane meters) or 3 (ECF); leading axes are free.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import sarkit.cphd as sc
import sarkit.sicd as ss
import sarkit.wgs84 as wgs84

from sarsil.xmlparam import q


def _xyz(node, path: str) -> np.ndarray:
    e = node.find(q(path))
    return np.array([float(e.findtext(q(k))) for k in ("X", "Y", "Z")])


@dataclass(frozen=True)
class SicdGeometry:
    """Geometry of one SICD image (read from its XML; pixel data are not touched)."""
    xmltree: object
    num_rows: int
    num_cols: int
    scp_pixel_row: int
    scp_pixel_col: int
    scp_ecf: np.ndarray
    scp_llh: np.ndarray            # (lat deg, lon deg, HAE m)
    row_uvect: np.ndarray          # ECF unit vector of increasing row
    col_uvect: np.ndarray          # ECF unit vector of increasing column
    row_ss: float                  # m per row
    col_ss: float                  # m per column
    declared_image_corners_lat_lon: np.ndarray   # (4, 2) FRFC, FRLC, LRLC, LRFC

    @classmethod
    def from_sicd(cls, path: str | Path) -> "SicdGeometry":
        with open(path, "rb") as fh:
            xml = ss.NitfReader(fh).metadata.xmltree
        return cls.from_xmltree(xml)

    @classmethod
    def from_xmltree(cls, xml) -> "SicdGeometry":
        r = xml.getroot()
        t = lambda p: r.findtext(q(p))  # noqa: E731
        scp = _xyz(r, "GeoData/SCP/ECF")
        corners = np.array([[float(c.findtext(q("Lat"))), float(c.findtext(q("Lon")))]
                            for c in r.findall(q("GeoData/ImageCorners/ICP"))])
        return cls(xml, int(t("ImageData/NumRows")), int(t("ImageData/NumCols")),
                   int(t("ImageData/SCPPixel/Row")), int(t("ImageData/SCPPixel/Col")),
                   scp, wgs84.cartesian_to_geodetic(scp), _xyz(r, "Grid/Row/UVectECF"), _xyz(r, "Grid/Col/UVectECF"),
                   float(t("Grid/Row/SS")), float(t("Grid/Col/SS")), corners)

    # ---- pixel <-> image-plane meters (SCP centered)
    def pixel_to_plane_m(self, rowcol) -> np.ndarray:
        return ss.rowcol_to_xrowycol(self.xmltree, np.asarray(rowcol, dtype=float))

    def plane_m_to_pixel(self, xrowycol) -> np.ndarray:
        return ss.xrowycol_to_rowcol(self.xmltree, np.asarray(xrowycol, dtype=float))

    # ---- slant image plane <-> ECF (points lie in the plane through the SCP spanned by the grid vectors)
    def plane_m_to_ecf_slant(self, xrowycol) -> np.ndarray:
        xy = np.asarray(xrowycol, dtype=float)
        return self.scp_ecf + xy[..., :1] * self.row_uvect + xy[..., 1:2] * self.col_uvect

    def ecf_to_plane_m_slant(self, ecf) -> np.ndarray:
        """In-plane coordinates of ECF points; the out-of-plane component is discarded."""
        d = np.asarray(ecf, dtype=float) - self.scp_ecf
        return np.stack([d @ self.row_uvect, d @ self.col_uvect], axis=-1)

    def pixel_to_ecf_slant(self, rowcol) -> np.ndarray:
        return self.plane_m_to_ecf_slant(self.pixel_to_plane_m(rowcol))

    # ---- projections onto the ground (SICD Volume 3)
    def up_at_scp(self) -> np.ndarray:
        return wgs84.up(self.scp_llh)

    def pixel_to_ecf_ground(self, rowcol, gref=None, ugpn=None) -> np.ndarray:
        """Project pixels to the plane through `gref` (default SCP) with unit normal `ugpn` (default up at SCP)."""
        gref = self.scp_ecf if gref is None else np.asarray(gref, dtype=float)
        ugpn = self.up_at_scp() if ugpn is None else np.asarray(ugpn, dtype=float)
        pts, _, ok = ss.image_to_ground_plane(self.xmltree, self.pixel_to_plane_m(rowcol), gref, ugpn)
        if not ok:
            raise ValueError("ground plane projection failed for some pixels")
        return pts

    def pixel_to_ecf_hae(self, rowcol, hae_m: float) -> np.ndarray:
        """Project pixels to the constant-height ellipsoidal surface HAE = hae_m."""
        pts, _, ok = ss.image_to_constant_hae_surface(self.xmltree, self.pixel_to_plane_m(rowcol), hae_m)
        if not ok:
            raise ValueError("constant-HAE projection failed for some pixels")
        return pts

    def ecf_to_pixel(self, ecf) -> np.ndarray:
        """Image pixel (row, col) of scene points (SICD scene-to-image projection)."""
        xy, _, ok = ss.scene_to_image(self.xmltree, np.asarray(ecf, dtype=float))
        if not ok:
            raise ValueError("scene-to-image projection failed for some points")
        return self.plane_m_to_pixel(xy)

    # ---- CPHD image-area coordinates
    @staticmethod
    def ecf_to_cphd_iac(cphd_xmltree, ecf) -> np.ndarray:
        return sc.ecf_to_iac(cphd_xmltree, np.asarray(ecf, dtype=float))
