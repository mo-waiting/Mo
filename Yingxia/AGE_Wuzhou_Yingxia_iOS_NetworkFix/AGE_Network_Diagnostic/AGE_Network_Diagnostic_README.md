# AGE Network Diagnostic (Yingxia iOS)

This temporary JS Spider checks the same native `http()` adapter used by the AGE source.
It tests:

- `https://example.com/`
- `https://www.baidu.com/`
- `https://www.agedm.io/update`
- `https://agedm.io/update`
- the AGE catalog URL used in the current test

## Import

Import `AGE_Network_Diagnostic_subscription.json` as a temporary subscription. Ensure `AGE_Network_Diagnostic.js` is hosted at the same directory/path referred to by the JSON `api` value, or use a subscription JSON with the correct absolute API URL.

Open source **AGE网络诊断（临时）** → category **网络连接测试**. Each result is shown as one item. Open an item to see status, final URL, response headers and a short body preview, or the caught error.

## Interpretation

- If Example and Baidu return 200 but AGE returns `code=empty` / request error, the failure is AGE-host-specific (network route, TLS, CDN/WAF, or domain behavior), not a general QuickJS HTTP failure.
- If all targets fail, investigate Yingxia's app-level network path, proxy/VPN/DNS, or the installed app build before changing the AGE spider.
- If `www.agedm.io` fails but `agedm.io` succeeds, the spider can be switched to the working hostname.
- An ordinary HTTP 403/404 is still a successful network connection; it is displayed as an HTTP status, not a network error.

Remove this temporary source after testing.
