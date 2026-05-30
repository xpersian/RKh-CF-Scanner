# RKh-CFS v0.1.4 | @pingplas_channel ⚡

اسکنر **Clean-IP کلادفلر** برای کانفیگ‌های **VLESS** با تست واقعی از طریق **Xray Core**.

RKh-CFS هر IP را با همان کانفیگی که وارد می‌کنی تست می‌کند. برای هر تارگت فقط آدرس سرور در outbound عوض می‌شود و چیزهای مهم مثل `UUID`، `SNI`، `Host`، `Path`، نوع transport، TLS و Reality از کانفیگ اصلی حفظ می‌شوند. بعد Xray اجرا می‌شود و یک درخواست واقعی از داخل تونل عبور می‌کند؛ پس نتیجه فقط Ping یا TCP Check ساده نیست.

---

## 📦 نسخه‌ها

| نسخه | فایل اصلی | محیط اجرا |
|---|---|---|
| Windows / Python | `RKh-CFS-v0.1.4.py` | ویندوز با Python و `xray.exe` |
| Android / Termux | `RKh-CFS-Termux-v0.1.4.py` | اندروید با Termux و باینری `xray` مخصوص Android/Linux |

---

## ✨ تغییرات مهم v0.1.4

- TUI رنگی‌تر و مرتب‌تر با Rich.
- گزینه برگشت در مراحل اصلی اضافه شده.
- منوها هم با عدد کار می‌کنند، هم با کلیدهای جهت‌دار:
  - `↑ / ↓`
  - `Space`
  - `Enter`
- دو حالت اصلی برای انتخاب تارگت:
  1. ورود دستی IP / CIDR / Range
  2. استفاده از لیست آماده ISPها
- لیست ISPها به دو دسته تقسیم شده:
  - ISPهای ایران
  - ISPهای خارج
- بخش ورود دستی چندخطی شده و می‌توانی چندین رنج را یکجا Paste کنی.
- مقدار پیش‌فرض Maximum targets بی‌نهایت است؛ با Enter همه تارگت‌ها اسکن می‌شوند.
- اگر وسط scan، re-check یا speed-test کلید `Ctrl+C` بزنی، خروجی‌های جمع‌شده تا همان لحظه ذخیره می‌شوند.
- در مرحله `Re-checking Latency`، متن `5 real Xray test(s) per IP` برای تست واقعی چندباره هر IP نمایش داده می‌شود.
- نسخه Termux حالا با `run.sh` اجرا می‌شود و اسکریپت نصب جداگانه ندارد.

---

## 🚀 قابلیت‌ها

- تست واقعی VLESS با Xray Core
- ورود دستی IP، CIDR و Range
- امکان Paste کردن چندین تارگت به‌صورت یکجا
- لیست آماده ISPها
- دسته‌بندی ایران و خارج
- انتخاب چند ISP برای اسکن
- انتخاب تعداد Worker قبل از اسکن
- Re-check اختیاری برای latency
- Speed-test اختیاری
- خروجی TXT و CSV
- حالت CLI برای اجرای سریع‌تر و خودکار

---

## 🧭 مسیر انتخاب تارگت در TUI

بعد از وارد کردن کانفیگ VLESS، برنامه دو مسیر نشان می‌دهد:

```text
1) Manual IP ranges
2) ISP range list
```

اگر گزینه `ISP range list` را بزنی، بعدش دسته را انتخاب می‌کنی:

```text
1) Iran
2) International
```

بعد از ورود به دسته، می‌توانی یک یا چند ISP را انتخاب کنی.

کلیدها:

```text
↑ / ↓      جابه‌جایی
Space      انتخاب / حذف انتخاب
Enter      تأیید
B / Esc    برگشت
```

انتخاب عددی هم هنوز فعال است:

```text
1
1,3,5
2-6
all
```

---

## 📝 ورود دستی تارگت‌ها

در حالت Manual می‌توانی این مدل‌ها را وارد کنی:

```text
104.16.0.1
104.16.0.0/24
104.16.0.1-104.16.0.255
```

می‌توانی چندین خط را یکجا Paste کنی:

```text
104.16.0.0/24
172.64.0.0/24
188.114.96.0-188.114.99.255
```

بعد از آخرین خط، روی یک خط خالی Enter بزن تا برنامه برود مرحله بعد. یعنی معمولاً بعد از Paste کردن لیست، کافی است **دوبار Enter** بزنی.

---

## 🎯 Maximum targets

وقتی برنامه این را پرسید:

```text
Maximum targets to load/scan (default ∞)
```

اگر فقط Enter بزنی، همه تارگت‌های لودشده اسکن می‌شوند.

اگر می‌خواهی رنج‌های خیلی بزرگ محدود شوند، عدد وارد کن:

```text
5000
```

وقتی محدودیت عددی وارد شود، برنامه از کل رنج‌ها نمونه‌برداری یکنواخت انجام می‌دهد و فقط از اول رنج‌ها شروع نمی‌کند.

---

## 📁 خروجی‌ها

نتایج داخل پوشه `results` ذخیره می‌شوند:

```text
results/clean_ips.txt
results/clean_ips.csv
results/clean_ips_rechecked.txt
results/clean_ips_speed_tested.csv
```

اگر اسکن با `Ctrl+C` متوقف شود، خروجی ناقص ولی ذخیره‌شده با نام جدا ساخته می‌شود، مثل:

```text
results/clean_ips_interrupted.txt
```

---

# 🪟 نصب و اجرا در ویندوز

## ساختار پوشه

بعد از Extract کردن نسخه ویندوز، ساختار پیشنهادی این است:

```text
RKh-CFS-v0.1.4/
├─ RKh-CFS-v0.1.4.py
├─ run_windows.bat
├─ requirements.txt
├─ xray.exe
├─ geoip.dat
├─ geosite.dat
├─ ip-ranges/
├─ configs/temp/
└─ results/
```

این فایل‌ها داخل پکیج قرار داده نشده‌اند و باید کنار فایل Python باشند:

```text
xray.exe
geoip.dat
geosite.dat
```

## نصب پیش‌نیازها

داخل پوشه برنامه PowerShell باز کن و بزن:

```powershell
py -m pip install -r requirements.txt
```

## اجرا

```powershell
py RKh-CFS-v0.1.4.py
```

یا روی فایل زیر دابل‌کلیک کن:

```text
run_windows.bat
```

---

# 🤖 نصب و اجرا در Android / Termux

پکیج Termux جداست و اسمش این است:

```text
RKh-CFS-Termux-v0.1.4.zip
```

این فایل‌ها داخل پکیج نیستند:

```text
xray
geoip.dat
geosite.dat
```

بعد از Extract کردن ZIP، این سه فایل را دستی کنار `run.sh` قرار بده.

## ساختار پوشه Termux

```text
RKh-CFS-Termux-v0.1.4/
├─ RKh-CFS-Termux-v0.1.4.py
├─ run.sh
├─ requirements.txt
├─ xray
├─ geoip.dat
├─ geosite.dat
├─ ip-ranges/
├─ configs/temp/
└─ results/
```

## نصب و اجرا در Termux

```bash
pkg update -y
pkg install -y unzip
pkg install python -y
pkg install wget unzip -y
mkdir -p RKh-CFS-Termux-v0.1.4
cd RKh-CFS-Termux-v0.1.4
wget https://github.com/rezakhosh78/RKh-CF-Scanner/releases/download/v0.1.4/RKh-CFS-Termux-v0.1.4.zip
unzip RKh-CFS-Termux-v0.1.4.zip
pip install -r requirements.txt
chmod +x run.sh
./run.sh
```

قبل از اجرای `./run.sh` مطمئن شو فایل‌های `xray`، `geoip.dat` و `geosite.dat` کنار `run.sh` هستند.

اگر لازم بود، به `xray` هم permission اجرا بده:

```bash
chmod +x xray
```

> اندروید نمی‌تواند `xray.exe` ویندوز را اجرا کند. برای Termux باید باینری Android/Linux با نام `xray` استفاده شود.

---

## 🧪 نمونه‌های CLI

نمایش لیست ISPها:

```bash
python RKh-CFS-v0.1.4.py --list-isps
```

اسکن همه ISPهای ایرانی:

```bash
python RKh-CFS-v0.1.4.py -c "vless://..." --isp-category iran --isp all --max-hosts 0
```

اسکن چند ISP از دسته بین‌المللی:

```bash
python RKh-CFS-v0.1.4.py -c "vless://..." --isp-category international --isp Fastly Nocix --max-hosts 3000
```

اسکن دستی:

```bash
python RKh-CFS-v0.1.4.py -c "vless://..." -t 104.16.0.0/24 172.64.0.0/24 --concurrency 20
```

---

## ⚙️ نکات کاربردی

- در ویندوز نام فایل Xray معمولاً باید `xray.exe` باشد.
- در Termux نام فایل باید `xray` باشد.
- فایل‌های `geoip.dat` و `geosite.dat` را کنار اسکریپت قرار بده.
- اگر کانفیگ Cloudflare داری، مقدارهای `SNI` و `Host` باید درست باشند.
- Worker بیشتر سرعت را بالا می‌برد، ولی اگر زیاد باشد ممکن است خطا، محدودیت شبکه، داغ شدن گوشی یا نتیجه ناپایدار بدهد.
- Worker پیشنهادی در ویندوز: `10` تا `30`
- Worker پیشنهادی در Termux: `5` تا `20`

---

## ⚠️ مسئولیت استفاده

RKh-CFS برای تست کانفیگ شخصی و رنج‌های مجاز ساخته شده است. مسئولیت استفاده از ابزار با خود کاربر است.

کانال: `@pingplas_channel`
