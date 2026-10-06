# Packet evidence

## Source and privacy

Captured on this Windows PC using Windows SIO_RCVALL on the active network interface.
Actual IP packet bytes were saved with the raw-IP link type (no Ethernet header was synthesized). Duplicate observations with the same endpoint tuple and UDP payload were removed.
Only actual UDP packets with ports 53 and 53003 were retained. Port 53003 was bound by our iterative resolver; background DNS traffic was excluded.

## Query and matching answer

Query packet 5 (original 7) and answer packet 6 (original 8) share transaction ID `0xde00`.
Query direction: `192.168.0.21:53003` → `163.152.11.6:53`; response reverses it.
The client host is 192.168.0.21. This is our PC.

## Delegation versus answer

Delegation: packet 2; ANCOUNT=0, authority section contains NS records. Answer: packet 6; ANCOUNT=1, A record in the answer section.

## Largest DNS response

Packet 8 (original 11): **384 DNS-message bytes** (excluding UDP/IP/Ethernet headers); 412 captured packet bytes (here the IP datagram).
It contains 0 answer RRs, 5 authority RRs, 10 additional RRs. The record names and resource data below explain its size:

```text
id 5754
opcode QUERY
rcode NOERROR
flags QR
;QUESTION
dns.google. IN A
;ANSWER
;AUTHORITY
google. 172800 IN NS ns-tld2.charlestonroadregistry.com.
google. 172800 IN NS ns-tld4.charlestonroadregistry.com.
google. 172800 IN NS ns-tld1.charlestonroadregistry.com.
google. 172800 IN NS ns-tld3.charlestonroadregistry.com.
google. 172800 IN NS ns-tld5.charlestonroadregistry.com.
;ADDITIONAL
ns-tld2.charlestonroadregistry.com. 172800 IN A 216.239.34.105
ns-tld2.charlestonroadregistry.com. 172800 IN AAAA 2001:4860:4802:34::69
ns-tld4.charlestonroadregistry.com. 172800 IN A 216.239.38.105
ns-tld4.charlestonroadregistry.com. 172800 IN AAAA 2001:4860:4802:38::69
ns-tld1.charlestonroadregistry.com. 172800 IN A 216.239.32.105
ns-tld1.charlestonroadregistry.com. 172800 IN AAAA 2001:4860:4802:32::69
ns-tld3.charlestonroadregistry.com. 172800 IN A 216.239.36.105
ns-tld3.charlestonroadregistry.com. 172800 IN AAAA 2001:4860:4802:36::69
ns-tld5.charlestonroadregistry.com. 172800 IN A 216.239.60.105
ns-tld5.charlestonroadregistry.com. 172800 IN AAAA 2001:4860:4805::69
```

## Retained packet map

| Output packet | Original packet | Direction | Transaction ID | DNS bytes | Answers | Authority | Additional |
|---:|---:|---|---|---:|---:|---:|---:|
| 1 | 1 | query | 0xddd4 | 33 | 0 | 0 | 0 |
| 2 | 2 | response | 0xddd4 | 341 | 0 | 6 | 10 |
| 3 | 4 | query | 0x3e45 | 33 | 0 | 0 | 0 |
| 4 | 5 | response | 0x3e45 | 105 | 0 | 2 | 2 |
| 5 | 7 | query | 0xde00 | 33 | 0 | 0 | 0 |
| 6 | 8 | response | 0xde00 | 49 | 1 | 0 | 0 |
| 7 | 10 | query | 0x167a | 28 | 0 | 0 | 0 |
| 8 | 11 | response | 0x167a | 384 | 0 | 5 | 10 |
| 9 | 13 | query | 0x01b5 | 28 | 0 | 0 | 0 |
| 10 | 14 | response | 0x01b5 | 281 | 0 | 4 | 8 |
| 11 | 16 | query | 0xc904 | 28 | 0 | 0 | 0 |
| 12 | 17 | response | 0xc904 | 60 | 2 | 0 | 0 |
