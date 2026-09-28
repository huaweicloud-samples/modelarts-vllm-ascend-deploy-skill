# ModelArts agency (委托)

Public-pool inference mounts OBS with a DEW AK/SK, but ModelArts **verifies the OBS path using the IAM agency**. A bound agency row is not enough: the agency must have OBS `ListBucket` + `GetObject`, and the OBS **授权范围** must include the bucket. Source: Huawei [OBS minimum for ModelArts](https://support.huaweicloud.com/permission-modelarts/permission-modelarts-007.html) and rain deploy (`Failed to verify the OBS path. Insufficient permission` while mounts “settled”).

## Who does what

| Step | Agent (this AK) | User (console / 主账号) |
|---|---|---|
| `GET /v2/{project_id}/authorizations` | yes | — |
| Bind current IAM user | `POST /v2/{project_id}/authorizations` | if 403 |
| Create ModelArts-named agency | `POST /v2/{project_id}/agency` | if 403 / 409 empty-shell |
| Attach OBS / SWR / DEW roles | **no** — needs `iam:agencies:createAgency` + role grant. `GET /v3.0/OS-AGENCY/agencies` **403** = this AK cannot | **yes** — §console |
| Inspect agency action list | no if IAM 403 | 查看权限 |

`admin` 用户组 **does not** imply `iam:agencies:*`. Do not bind leftover agencies that belong to another IAM user.

## Agent ladder (before CreateInferService)

1. `GET https://modelarts.{ma_region}.myhuaweicloud.com/v2/{project_id}/authorizations`
2. Ready **bind**: this AK’s `user_id` has `type=agency` and `content` is that user’s agency (`modelarts_agency*` / `ma_agency_*`). Another user’s row ≠ ready.
3. Missing bind → `POST /v2/{project_id}/agency` (`{}` or `{"agency_name_suffix":"<short>"}`) then `POST /v2/{project_id}/authorizations` `{"user_id":"<current>","type":"agency","content":"<agency_name>"}`.
4. `POST /agency` **409** name exists, or **200** but later OBS verify fails: the IAM agency is often an empty shell. Stop PUT. Send §console.
5. `GET /v3.0/OS-AGENCY/agencies` **403** or create **403** `iam:agencies:createAgency`: stop. Same §console. Do not keep CreateInferService/PUT.
6. After the user says 委托好了: GET authorizations again (name may change, e.g. `modelarts_agency_11ac`). One PUT. If events still `Failed to verify the OBS path. Insufficient permission`, stop — next is **授权范围** / missing `ListBucket`·`GetObject` / SSE-KMS, not another secret-name swap.

## Console (user, 推荐主账号)

Region = ModelArts region (not ECS). **权限管理 is per-region.** Authorizing OBS in 香港 / 华北 while the infer service is in **af-south-1** still fails path verify. Console top-left region must be **非洲-约翰内斯堡** before 添加委托.

1. 右上角区域切到本次 ModelArts 区域（默认 **非洲-约翰内斯堡 `af-south-1`**）。
2. **ModelArts → 权限管理 → 添加委托**（新版首次可点「立即授权」）。
3. 委托对象：**IAM 子用户 = 这对 AK 的用户**（不要绑别人）。个人账号也可「所有用户」。
4. 委托类型：**新增委托**（或已有同名再改权限）。勾选服务：
   - **对象存储 OBS**（全选；必须含 `ListBucket`、`GetObject`）
   - **容器镜像 SWR**（全选，拉镜像）
   - **数据加密 DEW / CSMS**（全选，读推理用 secret）
5. OBS **授权范围 = 所有资源**（推荐）。OBS 是**全局级服务**：选「指定区域项目」（哪怕是约翰内斯堡）也不会生效。若「指定资源」，JSON 须含 `obs:*:*:bucket:<桶>` 和 `obs:*:*:object:<桶>/*`。
6. 创建，提示输入 `Yes`。IAM 缓存 **10–15 分钟** 后策略才稳；刚保存就 PUT 仍可能 `Insufficient permission`。
7. 列表里点该用户 **查看权限**：搜索 `ListBucket`、`GetObject` 须存在。`ListAllMyBuckets` ≠ `ListBucket`。该弹窗**看不到授权范围** — 到 **IAM → 委托 → 该 agency → 权限** 看作用范围 / JSON `Resource`。

可选（让这把 AK 以后能自己建/查委托）：IAM → 用户组 → 授权 **Security Administrator**（全局）。部署本身不要求。

不要在 IAM 里建「委托给其他华为账号」那种跨账号委托。

## Minimum OBS actions

Path verify needs the first block. Full JSON is Huawei’s documented minimum so ModelArts can use OBS at all.

```
obs:bucket:HeadBucket
obs:bucket:ListBucket
obs:bucket:GetBucketLocation
obs:bucket:ListAllMyBuckets
obs:object:GetObject
obs:object:GetObjectVersion
obs:object:GetObjectAcl
obs:object:GetObjectVersionAcl
obs:object:PutObject
obs:object:DeleteObject
obs:object:DeleteObjectVersion
obs:object:ListMultipartUploadParts
obs:object:AbortMultipartUpload
obs:bucket:PutBucketAcl
obs:object:PutObjectAcl
```

Also: bucket **not SSE-KMS** (ModelArts rejects encrypted objects). Same region as ModelArts.

## Minimum DEW / SWR (infer)

DEW (read the CSMS secret used as `secret_name`): `csms:secret:list`, `csms:secretVersion:get` (and `csms:secret:get` / `csms:secret:getVersion` if the console template lists them).

SWR (pull the ARM image): `swr:namespace:getNamespace`, `swr:repo:getRepo`, `swr:repo:listRepoTags`, `swr:repository:getTag`, `swr:instance:createTempCredential`. Console: tick all SWR actions in the template.

One-click ticking **OBS+SWR+DEW 全选** is the intended user path; do not hand-build a thinner policy unless they insist.
