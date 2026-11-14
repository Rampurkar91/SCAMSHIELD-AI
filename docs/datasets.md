# Datasets and model limitations

## SMS Spam Collection
Official source: https://archive.ics.uci.edu/dataset/228/sms+spam+collection.
Creators: Tiago A. Almeida, José María Gómez Hidalgo, Akebo Yamakami (2011). UCI listing: CC BY 4.0; retain attribution. Download script uses `justmarkham/pycon-2016-tutorial`, `data/sms.tsv`, via GitHub's contents API. Provenance is in `backend/datasets/metadata/sms-source.json`.

The mirrored file has 5,574 physical lines; embedded line breaks and parsing mean line count is not a reliable message count. After parsing and deduplicating text the training pipeline retained **5,169** rows, with **4,135 training / 1,034 test**. Preprocessing: strip whitespace, Unicode accent normalization/lowercase in TF-IDF, word unigrams/bigrams, max 30,000 features, minimum document frequency 2. Logistic regression with balanced class weights; stratified random seed 42; 20% held out. Vectorizer fits on training data only.

Measured on this split: accuracy **0.9768**; spam precision **0.9023**, spam recall **0.9160**, spam F1 **0.9091**. False-positive rate (ham labeled spam) **0.0144**. Full metrics and confusion matrix are committed as JSON. These are not cross-domain, real-time scam or UPI-fraud metrics. Near-duplicate message templates may inflate results despite exact deduplication.

Only this trusted, separately trained English SMS artifact is loaded for message/UPI advisory labels. It never changes the rule-based risk score. Hindi/Marathi/UPI-domain classification is not validated. A spam label does not prove fraud; a ham label does not prove safety.

## Spambase
Official source: https://archive.ics.uci.edu/dataset/94/spambase.
Creators: Mark Hopkins, Erik Reeber, George Forman, Jaap Suermondt (1999). UCI listing: CC BY 4.0; retain attribution. Script mirror: `COM6012/ScalableML`, `Data/spambase.data`. Raw: **4,601** rows, **57 numeric features plus binary label**. Exact-row deduplication leaves **4,210**, with **3,368 train / 842 test**. StandardScaler + balanced logistic regression; stratified seed 42.

Measured accuracy **0.9359**, spam precision **0.9075**, recall **0.9345**, F1 **0.9208**, ham-as-spam false-positive rate **0.0632**. See metadata JSON for full matrix and source hash. This model is trained/evaluated offline only: pasted emails are not converted to the historic Spambase feature representation, so the application **does not falsely apply this model to raw email text**. Spam is not equivalent to phishing.

## URL datasets
PhishTank and URLhaus adapters are reputation lookups, not model training data. Phishing and malware distribution remain distinct. No comprehensive licensed benign/phishing/malware training dataset was available/validated here. No URL classifier was trained or activated. The training command accepts an operator-supplied CSV with `url,label` (`benign`, `phishing`, `malware`) and refuses single-class data. Review licensing, deduplicate by registrable domain and evaluate using time/domain-separated splits before deploying a URL model. The current random split command is a research baseline, not deployment validation.

## Synthetic Indian scenarios
`backend/datasets/upi/synthetic_examples.csv` has nine authored examples with `message_id,message_text,language,scam_category,label,source_type,source_reference`. They are transparently synthetic test fixtures under CC0-1.0, not harvested private conversations, real-world prevalence estimates or adequate training data. English, Hindi and Marathi examples help regression-test local rules only.

## Reproduction
See [exact setup commands](API_AND_DATASET_SETUP.md). Download scripts do not silently alter or redistribute data. Source metadata includes a SHA-256 and Git blob SHA. Joblib artifacts stay local and must be produced by a trusted operator, never accepted as uploads. Dependency versions are pinned in backend requirements; metrics can vary across future library versions/hardware. No voice dataset or private conversations are collected.
