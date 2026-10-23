# Security

## Secrets

Do not commit API keys, tokens or passwords. The DeepL key is read only from the
`DEEPL_API_KEY` environment variable:

```bash
export DEEPL_API_KEY='xxxxxxxx:fx'
```

`.env`, `.env.*` (except `.env.example`), `*.key`, `*.pem` and `secrets/` are
ignored by Git. If a real key was ever committed or posted publicly, revoke it
in the provider account and issue a new one.

## Reporting

For a security issue in the code, open a private security advisory or contact
the repository owner instead of publishing the details in an issue.
