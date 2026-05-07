# um-cli Integration in MediaTools

> [中文版](./INTEGRATION.zh.md)

## Purpose

Music and media decryption (e.g., `.ncm` encrypted formats).

## Status

**Optional** - Required only for decryption workflows.

## Maintenance

- Location: `bin/um-cli`
- Service: `backend/services/decryptor.py`
- CLI module: `modules/decryptor/`
- May require Go for local compilation

## Usage in MediaTools

| Feature | Module |
|---|---|
| Decryption | `modules/decryptor/` |
| Service | `backend/services/decryptor.py` |

```powershell
python -m cli.main decryptor run -i song.ncm
```

## Upstream

- Part of Unlock Music project
- Go-based CLI tool
- Original source: `vendor/um-cli/`
