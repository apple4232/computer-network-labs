# DNS / CDN measurement report

## Measurement scope

Networks actually measured: KT-current.
System DNS is the configured ISP resolver; Google and Quad9 are public anycast resolvers. Different provider addresses do not establish geographically distant endpoints.
Only successful address sets are compared; failures are not empty address sets.

## Third-party rule and table

Rule: a CNAME path crossing a known external CDN suffix is third-party evidence. Netflix is treated as an own CDN using the course reference. A path without these suffixes is unknown, not proof of no CDN.

| Site | Network | Chain length | Final zone | Third party? | Rule verdict |
|---|---|---:|---|---|---|
| www.microsoft.com | KT-current | 2 | akamaiedge.net | yes | known CDN suffix |
| www.netflix.com | KT-current | 1 | netflix.com | no | same operator |
| www.adobe.com | KT-current | 2 | akamai.net | yes | known CDN suffix |
| www.cnn.com | KT-current | 1 | fastly.net | yes | known CDN suffix |
| www.apple.com | KT-current | 3 | akamaiedge.net | yes | known CDN suffix |
| www.korea.ac.kr | KT-current | 0 | korea.ac.kr | no | direct university A record; course reference |
| www.stanford.edu | KT-current | 1 | netlifyglobalcdn.com | yes | known CDN suffix |
| www.bbc.co.uk | KT-current | 2 | fastly.net | yes | known CDN suffix |
| www.spotify.com | KT-current | 1 | fastly.net | yes | known CDN suffix |
| www.github.com | KT-current | 1 | github.com | unknown | no known CDN suffix; CNAME-only blind spot |
| www.wikipedia.org | KT-current | 1 | wikimedia.org | no | Wikipedia/Wikimedia operator equivalence |
| www.nytimes.com | KT-current | 3 | fastly.net | yes | known CDN suffix |

## Resolver steering number

7 of 9 CDN-hosted sites answered differently to a different resolver or measured network.
Across all comparable sites: 8 of 12. CDN-hosted here means a known CDN suffix or the course-confirmed Netflix own CDN.
This shows response variation, not that a selected replica is nearby: anycast location, cache timing, address rotation and resolver policy are confounders.

## Per-resolver address evidence

| Site | Network | Resolver | Server | A set / error |
|---|---|---|---|---|
| www.microsoft.com | KT-current | system | 168.126.63.1 | 184.28.184.92 |
| www.microsoft.com | KT-current | google | 8.8.8.8 | 184.28.184.92 |
| www.microsoft.com | KT-current | quad9 | 9.9.9.9 | 23.0.194.92 |
| www.netflix.com | KT-current | system | 168.126.63.1 | 207.45.72.1, 207.45.73.1 |
| www.netflix.com | KT-current | google | 8.8.8.8 | 207.45.72.1, 207.45.73.1 |
| www.netflix.com | KT-current | quad9 | 9.9.9.9 | 207.45.72.1, 207.45.73.1 |
| www.adobe.com | KT-current | system | 168.126.63.1 | 23.32.4.154, 23.32.4.176, 23.32.4.177, 23.32.4.178, 23.32.4.184, 23.32.4.185, 23.32.4.201, 23.32.4.210, 23.32.4.233 |
| www.adobe.com | KT-current | google | 8.8.8.8 | 23.32.4.107, 23.32.4.121, 23.32.4.136, 23.32.4.138, 23.32.4.32, 23.32.4.33, 23.32.4.34, 23.32.4.72, 23.32.4.9 |
| www.adobe.com | KT-current | quad9 | 9.9.9.9 | 23.219.78.45, 23.219.78.49 |
| www.cnn.com | KT-current | system | 168.126.63.1 | 146.75.51.5 |
| www.cnn.com | KT-current | google | 8.8.8.8 | 151.101.131.5, 151.101.195.5, 151.101.3.5, 151.101.67.5 |
| www.cnn.com | KT-current | quad9 | 9.9.9.9 | 151.101.131.5, 151.101.195.5, 151.101.3.5, 151.101.67.5 |
| www.apple.com | KT-current | system | 168.126.63.1 | 23.217.180.246 |
| www.apple.com | KT-current | google | 8.8.8.8 | 23.217.180.246 |
| www.apple.com | KT-current | quad9 | 9.9.9.9 | 23.0.193.49 |
| www.korea.ac.kr | KT-current | system | 168.126.63.1 | 163.152.6.10 |
| www.korea.ac.kr | KT-current | google | 8.8.8.8 | 163.152.6.10 |
| www.korea.ac.kr | KT-current | quad9 | 9.9.9.9 | 163.152.6.10 |
| www.stanford.edu | KT-current | system | 168.126.63.1 | 15.197.167.90, 3.33.186.135 |
| www.stanford.edu | KT-current | google | 8.8.8.8 | 15.197.167.90, 3.33.186.135 |
| www.stanford.edu | KT-current | quad9 | 9.9.9.9 | 15.197.167.90, 3.33.186.135 |
| www.bbc.co.uk | KT-current | system | 168.126.63.1 | 146.75.48.81 |
| www.bbc.co.uk | KT-current | google | 8.8.8.8 | 151.101.0.81, 151.101.128.81, 151.101.192.81, 151.101.64.81 |
| www.bbc.co.uk | KT-current | quad9 | 9.9.9.9 | 151.101.0.81, 151.101.128.81, 151.101.192.81, 151.101.64.81 |
| www.spotify.com | KT-current | system | 168.126.63.1 | 146.75.51.42 |
| www.spotify.com | KT-current | google | 8.8.8.8 | 151.101.131.42, 151.101.195.42, 151.101.3.42, 151.101.67.42 |
| www.spotify.com | KT-current | quad9 | 9.9.9.9 | 151.101.131.42, 151.101.195.42, 151.101.3.42, 151.101.67.42 |
| www.github.com | KT-current | system | 168.126.63.1 | 20.200.245.247 |
| www.github.com | KT-current | google | 8.8.8.8 | 20.200.245.247 |
| www.github.com | KT-current | quad9 | 9.9.9.9 | 20.27.177.113 |
| www.wikipedia.org | KT-current | system | 168.126.63.1 | 103.102.166.224 |
| www.wikipedia.org | KT-current | google | 8.8.8.8 | 103.102.166.224 |
| www.wikipedia.org | KT-current | quad9 | 9.9.9.9 | 103.102.166.224 |
| www.nytimes.com | KT-current | system | 168.126.63.1 | 146.75.49.164 |
| www.nytimes.com | KT-current | google | 8.8.8.8 | 151.101.1.164, 151.101.129.164, 151.101.193.164, 151.101.65.164 |
| www.nytimes.com | KT-current | quad9 | 9.9.9.9 | 151.101.1.164, 151.101.129.164, 151.101.193.164, 151.101.65.164 |

## Classification error and limits

Measured counterexample: www.wikipedia.org → dyna.wikimedia.org. The naive last-two-label rule incorrectly calls wikimedia.org a third party, although Wikimedia operates Wikipedia and its own hosting infrastructure. [Wikimedia operator and hosting evidence](https://wikimediafoundation.org/technology/).
Our initial narrow CDN suffix list also missed Stanford → stanford.netlifyglobalcdn.com. Adding Netlify fixes this false negative; this illustrates why a fixed suffix list needs review. [Netlify support confirms this hostname family](https://answers.netlify.com/t/how-can-i-change-which-netlify-site-my-hostname-is-pointing-to/3259).
bbc.co.uk ends in co.uk, a public suffix rather than an operator domain. A CNAME-only detector also misses a CDN using direct A/anycast addresses. The final rule returns unknown for cases with insufficient evidence.

## Capture / delegation / answer

See capture-analysis.md for source provenance, packet numbers, transaction IDs, largest DNS response and the observed answer/authority sections.

## Path (B): one network, different resolver distances

A second physical network was unavailable, as confirmed by the student. We use the task2.md path (B) resolver-distance comparison instead of B3.
Local configured ISP resolver: 168.126.63.1, median DNS exchange 10.15 ms. Google resolver: 8.8.8.8, median 37.13 ms; observed NSID `gpdns-nrt`.
Google documents the NSID suffix as the serving metro airport code; NRT identifies the Narita/Tokyo metro. [Google NSID documentation](https://developers.google.com/speed/public-dns/docs/troubleshooting). The observed times are from five identical A queries, and include DNS processing; they are not pure propagation delay.
For this ISP-versus-NRT comparison alone, **5 of 9 CDN-hosted sites** returned different address sets.
The three-resolver result above is a broader comparison including Quad9. This substitutes resolver vantage points for changing the client network, so it does not demonstrate that moving the same laptop changes its selected replica. We also did not measure replica location or HTTP RTT, so the claim “nearby replica” remains unproven. Do not describe this as two physical networks or Korea-versus-US.
