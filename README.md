<div align="center">

<img src="./assets/portrait.svg" width="460" alt="Arqam Ahmad Siddiqui"/>

<img src="./assets/stats.svg" width="620" alt="Contributions in the last year"/>

[arqam365.com](https://www.arqam365.com/) &nbsp;·&nbsp;
[revzion.in](https://www.revzion.in/) &nbsp;·&nbsp;
[linkedin](https://linkedin.com/in/arqam365) &nbsp;·&nbsp;
[x](https://x.com/arqam365) &nbsp;·&nbsp;
[email](mailto:connect@revzion.in)

</div>

<img src="./assets/hd-about.svg" width="620" alt="about"/>

> Founder and CEO of [Revzion](https://www.revzion.in/), in Jhansi, India.<br>
> Systems over hype. Architecture is judged by what survives contact with load.

I run the company and stay in the codebase. Most of what I build sits where<br>
Kotlin Multiplatform meets real-time architecture, BLE, and backends that have<br>
to hold up under real traffic rather than a staging demo.

<img src="./assets/hd-stack.svg" width="620" alt="stack"/>

<samp>kotlin &nbsp; kmp &nbsp; compose &nbsp; ktor &nbsp; android &nbsp; ble &nbsp; mongodb &nbsp; postgres &nbsp; typescript &nbsp; next.js &nbsp; docker &nbsp; gcp</samp>

<img src="./assets/hd-work.svg" width="620" alt="work"/>

**[Revzion](https://www.revzion.in/)** &nbsp;·&nbsp; <samp>kotlin, ktor, mongodb</samp><br>
SaaS platforms, AI systems and cross-platform delivery for startups and<br>
enterprises. Auth flows, role-based access, scalable APIs, deploy pipelines.

**Evolwe Ring** &nbsp;·&nbsp; <samp>kmp, compose, ble</samp><br>
Wearable ring companion app. Real-time BLE connectivity, sync, and state<br>
consistency held identical across Android and iOS from one codebase.

**Merakaam** &nbsp;·&nbsp; <samp>kmp, compose, ktor</samp><br>
Cross-platform product platform: shared domain logic, native UI layers,<br>
no second stack to keep in step.

**Suraksha Kawach** &nbsp;·&nbsp; <samp>android, web</samp><br>
Personal safety platform, web and Android, built at<br>
[Panthar InfoHub](https://www.pantharinfohub.com/).

<img src="./assets/hd-stats.svg" width="620" alt="stats"/>

<div align="center">

<img src="./assets/streak.svg" width="620" alt="Current and longest streak"/>

<img src="./assets/langs.svg" width="620" alt="Top languages by bytes and by repo"/>

<img src="./assets/year.svg" width="620" alt="The last year, one character per day"/>

</div>

<img src="./assets/hd-about-this-page.svg" width="620" alt="about this page"/>

Every graphic here is generated, not embedded from anyone else's server.<br>
`portrait.svg` is a photo pushed through a character ramp by<br>
[`scripts/make_portrait.py`](scripts/make_portrait.py); the stat graphics and<br>
these section headings are drawn by [a scheduled action](.github/workflows/stats.yml)<br>
straight from the GitHub GraphQL API, once a day, committing only what changed.

They animate with SMIL inside the SVG, because GitHub strips scripts from<br>
READMEs — and since nothing loads from a third party, nothing here can<br>
rate-limit or go dark. This page used to carry a trophy, an activity graph, a<br>
contributor-stats card and a visitor counter; all four were returning `402` or<br>
`404` to anyone who visited. The headings are SVGs for the same reason: GitHub<br>
also strips CSS, so an image is the only way to put this page's own typeface<br>
on them.

The typeface is [JetBrains Mono](scripts/fonts), subset to just the characters<br>
each graphic draws and inlined as base64. That isn't only for looks: the<br>
portrait's grid assumes an advance width of exactly 0.600 em, and a viewer<br>
whose default monospace is narrower would otherwise see it squeezed. An<br>
external font URL cannot work — these SVGs load through `<img>`, and browsers<br>
refuse subresource fetches for an image document.

Language totals cover public repositories only. `year.svg` uses the portrait's<br>
character ramp: `:` `+` `#` `@`, quiet to loud, scaled to a busy-but-typical<br>
day so an ordinary one doesn't round away to blank.
