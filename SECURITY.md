# Security policy

Report vulnerabilities privately to security@hybridcloudworks.com (or via GitHub private vulnerability reporting). Please do not open public issues for security findings. Expect an acknowledgement within 3 business days.

Scope highlights: the lab processes uploaded Resource Graph exports in memory only, never connects to a cloud, holds no credentials and has no execution surface; uploads are gated by human verification (fail closed, action and hostname bound); per-assessment owner tokens are hashed and compared in constant time; logs carry no visitor data; the container runs on a bridge network with no host mounts. See `docs/security/threat-model.md`. The engine is an interim port of `https://github.com/saulpatinojr/HCW-NetworkEyes_App`; a rule-logic issue that also exists there is reported there as well. Supported version: `main`.
