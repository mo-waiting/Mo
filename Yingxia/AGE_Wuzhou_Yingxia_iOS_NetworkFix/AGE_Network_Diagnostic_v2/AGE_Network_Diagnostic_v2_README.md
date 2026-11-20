# AGE Network Diagnostic v2

This temporary Yingxia JS Spider checks the official AGE domain and the easy-to-remember aliases listed by AGE's official URL-release repository: `www.age.tv`, `www.agedm.com`, and `agefans.com`.

For each alias it performs two requests:
- `redirect: 0`: do not follow redirects; inspect the HTTP status and `Location` header.
- `redirect: 1`: follow redirects; inspect the final URL and response.

It also checks `example.com` and Baidu as baselines. The plugin uses `http()` and does not use Node.js modules, `require`, `fetch`, or WebAssembly.

## Install

1. Put `AGE_Network_Diagnostic_v2.js` and `AGE_Network_Diagnostic_v2_subscription.json` in the same folder or server directory.
2. Import the JSON subscription. Keep the JS relative path unchanged.
3. Open `AGE备用域名诊断（临时）` → `网络测试`.
4. Send a screenshot of all result cards. Especially useful fields are `code`, `bytes`, `final`, and `location`.

This is a diagnostic-only source; it does not replace the AGE playback spider.
