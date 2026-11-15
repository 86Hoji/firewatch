# References

All external resources used by FIREWATCH: data, imagery, code, fonts, methods and literature. This is the text for the
"References" field of the NASA Space Apps project submission.

## NASA data

1. **NASA FIRMS (Fire Information for Resource Management System)**: archive downloads of active fire detections for
   Kazakhstan, Uzbekistan, Turkmenistan, Kyrgyzstan, Tajikistan, Portugal, Australia, Brazil, USA and India.
   We acknowledge the use of data from NASA's FIRMS (https://firms.modaps.eosdis.nasa.gov), part of NASA's Land,
   Atmosphere Near real-time Capability for EOS (LANCE) and Earth Science Data and Information System (ESDIS).
   - MODIS Collection 6.1 Hotspot / Active Fire Detections MCD14ML (standard), doi:10.5067/FIRMS/MODIS/MCD14ML;
     MCD14DL (near real-time), doi:10.5067/FIRMS/MODIS/MCD14DL.NRT.0061.
   - VIIRS S-NPP 375 m I-Band Active Fire Product (VNP14IMGTDL_NRT), doi:10.5067/FIRMS/VIIRS/VNP14IMGT_NRT.002.
   - VIIRS NOAA-20 (JPSS-1) 375 m I-Band Active Fire Product (VJ114IMGTDL_NRT), doi:10.5067/FIRMS/VIIRS/VJ114IMGT_NRT.002.
2. **MODIS MCD64A1 Collection 6.1 burned area.** Giglio, L., Justice, C., Boschetti, L., Roy, D. (2021).
   *MODIS/Terra+Aqua Burned Area Monthly L3 Global 500m SIN Grid V061*. NASA EOSDIS Land Processes DAAC.
   doi:10.5067/MODIS/MCD64A1.061. Used as monthly country totals (`data/external/burned_area.csv`) for the
   independent check of the 2012 seam.
3. **NASA GIBS, VIIRS Black Marble** night-lights basemap on the website (layer `VIIRS_Black_Marble`, 2016). We
   acknowledge the use of imagery provided by services from NASA's Global Imagery Browse Services (GIBS), part of
   NASA's Earth Science Data and Information System (ESDIS): https://gibs.earthdata.nasa.gov.
   Product: Román, M.O. et al. (2018). NASA's Black Marble nighttime lights product suite. *Remote Sensing of
   Environment* 210, 113–143. doi:10.1016/j.rse.2018.03.017.

## Other data

4. **geoBoundaries** ADM1 boundaries (gbOpen), CC BY 4.0: Runfola, D. et al. (2020). geoBoundaries: A global database of
   political administrative boundaries. *PLOS ONE* 15(4), e0231866. doi:10.1371/journal.pone.0231866.
   https://www.geoboundaries.org
5. **Natural Earth** country borders (public domain), via the `world-atlas` npm package (ISC):
   https://www.naturalearthdata.com, https://github.com/topojson/world-atlas

## Code

6. **Baseline pipeline `fire-regimes`** (Elbek, the team's own earlier work), imported into this repository on
   2026-11-14 and audited in `docs/AUDIT.md`.
7. **Python libraries:** pandas, NumPy, SciPy, PyArrow, DuckDB (MIT), Uber H3 / h3-py (Apache-2.0), GeoPandas,
   Shapely, matplotlib, FastAPI, Uvicorn, Pydantic, Requests, PyYAML, python-dotenv, pytest, httpx (all
   open-source licenses: BSD, MIT or Apache-2.0).
8. **Web libraries:** React, React Router, MapLibre GL JS (BSD-3-Clause), deck.gl (MIT), Apache ECharts
   (Apache-2.0), h3-js (Apache-2.0), framer-motion, Lenis, Zustand, Vite, Tailwind CSS, TypeScript,
   topojson-client, Playwright (MIT / ISC / Apache-2.0 / BSD).
9. **Fonts:** Geist (Vercel) and Instrument Serif, SIL Open Font License 1.1, via Fontsource.

## Methods and literature

10. Schroeder, W., Oliva, P., Giglio, L., Csiszar, I. (2014). The New VIIRS 375 m active fire detection data product:
    Algorithm description and initial assessment. *Remote Sensing of Environment* 143, 85–96.
    doi:10.1016/j.rse.2013.12.008.
11. Giglio, L., Schroeder, W., Justice, C.O. (2016). The collection 6 MODIS active fire detection algorithm and fire
    products. *Remote Sensing of Environment* 178, 31–41. doi:10.1016/j.rse.2016.02.054.
12. Hao, W. et al. (2021). Wetter environment and increased grazing reduced the area burned in northern Eurasia from
    2002 to 2016. *Biogeosciences* 18, 2559–2572. doi:10.5194/bg-18-2559-2021.
13. Near-real-time extension to the Global Fire Emissions Database (GFED5), *Earth System Science Data* 18, 7535
    (2026). https://essd.copernicus.org/articles/18/7535/2026/
14. Vadrevu, K., Lasko, K. et al. (2018). Intercomparison of MODIS AQUA and VIIRS I-Band Fires and Emissions in an
    Agricultural Landscape. https://pmc.ncbi.nlm.nih.gov/articles/PMC6108185/
15. Fire Detection and Fire Radiative Power in Forests and Low-Biomass Lands in Northeast Asia: MODIS versus VIIRS
    Fire Products. *Remote Sensing* (2020). https://www.mdpi.com/2072-4292/12/18/2870
16. The Transition from MODIS to VIIRS for Global Volcano Thermal Monitoring.
    https://pmc.ncbi.nlm.nih.gov/articles/PMC8914890/
17. Newey, W.K., West, K.D. (1987). A simple, positive semi-definite, heteroskedasticity and autocorrelation
    consistent covariance matrix. *Econometrica* 55(3), 703–708 (standard errors of the 2012 step test).
18. Pettitt, A.N. (1979). A non-parametric approach to the change-point problem. *Applied Statistics* 28(2), 126–135
    (change-point test).
19. Conformal prediction (interval method): Vovk, V., Gammerman, A., Shafer, G. (2005). *Algorithmic Learning in a
    Random World*. Springer; Angelopoulos, A.N., Bates, S. (2021). A Gentle Introduction to Conformal Prediction.
    arXiv:2107.07511.

## AI assistance

20. Claude (Anthropic) was used as a coding and analysis assistant: code review, the methodology audit
    (`docs/HARMONIZATION_REVIEW.md`), validation scripts, README and documentation drafts. All numbers come from the
    pipeline and reports in this repository and were checked by re-running them.
