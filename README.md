# RKh-CFS v0.1 | @pingplas_channel

User-friendly Cloudflare Clean-IP Scanner for VLESS + Xray Core.

The scanner tests each candidate IP with the VLESS configuration you paste. It starts Xray Core, routes a real request through the local SOCKS proxy, and records only working IPs with measured latency.

## Folder layout

Place these files in the same folder:

```text
RKh-CFS/
├─ RKh-CFS-v0.1_2.py
├─ run_windows.bat
├─ requirements.txt
├─ xray.exe
├─ geoip.dat
├─ geosite.dat
├─ results/
└─ configs/temp/
```

`xray.exe`, `geoip.dat`, and `geosite.dat` are not bundled here. Download Xray Core separately and put them beside the script.

## Install

```powershell
py -m pip install -r requirements.txt
```

## Run interactive UI

```powershell
py RKh-CFS-v0.1_2.py
```

or double-click:

```text
run_windows.bat
```

## New in this build

- Fixed header: `RKh-CFS v0.1 | @pingplas_channel`
- Asks for scan workers before scanning
- Keeps technical defaults hidden where possible
- After the first scan, asks whether to re-check latency for working IPs
- Re-check can run 5 tests per IP by default, or any count you choose
- Re-check uses Xray Core again for every latency test
- Saves updated sorted TXT and CSV output

## CLI mode

```powershell
py RKh-CFS-v0.1_2.py -c "vless://..." -t 104.16.0.0/24 --concurrency 10
```

Run a second latency check from CLI:

```powershell
py RKh-CFS-v0.1_2.py -c "vless://..." -t 104.16.0.0/24 --concurrency 20 --recheck --recheck-samples 5 --recheck-workers 10
```

## Output

Results are saved to:

```text
results/clean_ips.txt
results/clean_ips.csv
```

Use only on IPs/ranges you own or are authorized to test. Keep concurrency modest.
