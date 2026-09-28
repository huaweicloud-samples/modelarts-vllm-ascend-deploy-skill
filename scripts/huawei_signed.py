#!/usr/bin/env python3
"""Sign one Huawei Cloud REST call. Env: HUAWEI_AK, HUAWEI_SK, optional HUAWEI_PROJECT_ID. Never print SK."""
from __future__ import annotations

import os
import sys
import urllib.error
import urllib.request
from urllib.parse import parse_qsl, urlparse

from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkcore.sdk_request import SdkRequest
from huaweicloudsdkcore.signer.signer import Signer


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: huawei_signed.py METHOD URL [body.json]", file=sys.stderr)
        return 2
    ak = os.environ.get("HUAWEI_AK") or os.environ.get("huawei-ak")
    sk = os.environ.get("HUAWEI_SK") or os.environ.get("huawei-sk")
    project = os.environ.get("HUAWEI_PROJECT_ID") or os.environ.get("huawei-project-id") or ""
    if not ak or not sk:
        print("missing HUAWEI_AK / HUAWEI_SK", file=sys.stderr)
        return 2
    method, url = sys.argv[1].upper(), sys.argv[2]
    body = ""
    if len(sys.argv) > 3:
        with open(sys.argv[3], encoding="utf-8") as f:
            body = f.read()
    p = urlparse(url)
    path = p.path or "/"
    query = list(parse_qsl(p.query, keep_blank_values=True))
    headers = {"Content-Type": "application/json"} if body else {}
    cred = BasicCredentials(ak, sk, project or None)
    req = SdkRequest(
        method=method,
        schema=p.scheme,
        host=p.netloc,
        resource_path=path,
        uri=path,
        query_params=query,
        header_params=headers,
        body=body,
    )
    Signer(cred).sign(req)
    data = body.encode() if body else None
    http = urllib.request.Request(
        url, data=data, method=method, headers=dict(req.header_params)
    )
    try:
        with urllib.request.urlopen(http, timeout=120) as resp:
            print(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(e.read().decode(), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
