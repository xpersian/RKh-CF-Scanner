# RKh-CFS Termux v0.1.4 - نسخه Android / Termux

این نسخه برای اجرای مستقیم داخل Termux آماده شده است.

## نصب و اجرا در Termux

دستورهای زیر را دقیقاً داخل Termux اجرا کنید:

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

## فایل‌هایی که باید دستی اضافه کنید

این پکیج عمداً فایل‌های زیر را ندارد و باید خودتان آن‌ها را کنار `run.sh` و فایل Python قرار دهید:

```text
xray
geoip.dat
geosite.dat
```

ساختار پوشه بعد از Extract و اضافه کردن فایل‌ها:

```text
RKh-CFS-Termux-v0.1.4/
├── RKh-CFS-Termux-v0.1.4.py
├── run.sh
├── requirements.txt
├── xray
├── geoip.dat
├── geosite.dat
├── ip-ranges/
├── configs/
└── results/
```

بعد از قرار دادن فایل `xray`، این دستور را هم بزنید:

```bash
chmod +x xray
```

سپس برنامه را اجرا کنید:

```bash
./run.sh
```

## امکانات TUI

- حرکت با کلیدهای بالا/پایین
- انتخاب چندتایی با Space
- تأیید با Enter
- برگشت با `b`، `back` یا `Esc`
- انتخاب عددی مثل `1`، `1,3,5`، `2-6` و `all`


## انتخاب URL تست Latency 🌐

در مرحله تنظیمات اسکن، برنامه از شما می‌پرسد درخواست تست latency به کدام endpoint ارسال شود. انتخاب با کلیدهای بالا/پایین انجام می‌شود و با Enter تأیید می‌کنید. انتخاب عددی هم همچنان کار می‌کند.

گزینه پیش‌فرض روی Google gstatic است:

```text
https://www.gstatic.com/generate_204
```

گزینه‌های آماده داخل برنامه:

```text
https://www.gstatic.com/generate_204
https://cp.cloudflare.com/generate_204
https://edge.microsoft.com/captiveportal/generate_204
https://connectivitycheck.gstatic.com/generate_204
```

برای اینترنت ایران، اگر یک گزینه timeout داد یا ناپایدار بود، می‌توانید از همین مرحله گزینه دیگری را انتخاب کنید. 👍

## ورودی دستی IP / CIDR / Range

در بخش Manual می‌توانید چندین IP، ساب‌نت یا رنج را یکجا Paste کنید.

بعد از آخرین خط، روی خط خالی Enter بزنید تا برنامه به مرحله بعد برود. معمولاً یعنی بعد از Paste کردن، دوبار Enter بزنید.

نمونه:

```text
1.1.1.1
1.0.0.0/24
104.16.0.0-104.16.0.255
```

## Maximum targets

مقدار پیش‌فرض `Maximum targets to load/scan` برابر بی‌نهایت است.

یعنی اگر فقط Enter بزنید، همه IPهای داخل رنج‌های انتخاب‌شده اسکن می‌شوند. برای محدود کردن تعداد، یک عدد وارد کنید.

## ذخیره خروجی هنگام Ctrl+C

اگر وسط scan، re-check یا speed-test کلید `Ctrl+C` را بزنید، نتیجه‌های جمع‌شده تا همان لحظه داخل پوشه `results` ذخیره می‌شوند.

## نکته Termux

اگر در بعضی گوشی‌ها کلیدهای جهت‌دار درست کار نکردند، حالت انتخاب عددی همچنان فعال است.
