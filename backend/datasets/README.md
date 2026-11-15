# Dataset registry

See [the dataset guide](../../docs/datasets.md) and [API/dataset setup](../../docs/API_AND_DATASET_SETUP.md).

- `sms/`: local-only UCI SMS mirror TSV (ignored).
- `email/`: local-only numeric UCI Spambase CSV (ignored).
- `phishing/`: reserved for operator-supplied, licensed, independently labeled URL data; none downloaded or trained in this release.
- `upi/synthetic_examples.csv`: nine authored English/Hindi/Marathi educational fixtures, explicitly marked synthetic. Not real-world measurements or an adequate training set. Available under CC0-1.0 for testing and reuse.
- `voice/`: no audio dataset collected or redistributed.
- `metadata/`: source provenance, hashes and evaluation metrics; no private message text.

UCI official listings identify the SMS Spam Collection and Spambase as CC BY 4.0. Review current official license and attribution requirements before downloading/reusing. Mirrors are recorded as mirrors, not official endpoints. Third-party raw data is not redistributed in this repository. The downloader records exact Git blob and SHA-256 versions, so upstream changes are visible. Metrics apply only to the recorded version and split.
