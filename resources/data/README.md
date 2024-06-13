# Data

This directory is used to host the data set(s).

Supported data sets:
- [NatCS](https://aclanthology.org/2023.findings-acl.613/) (language: en, task: intent clustering and open intent induction): hosted via [GitHub](https://github.com/amazon-science/dstc11-track2-intent-induction/tree/main)
- [Teacher-Student Chatroom Corpus V2](https://aclanthology.org/2022.nlp4call-1.3/) (language: en, task: TBD): hosted via [Google Drive](https://drive.google.com/file/d/1QqBxKSwvAaIf0SytWROpVILLVuev3S1Q/view?usp=share_link))
  - [V1](https://aclanthology.org/2020.nlp4call-1.2/) (language: en, task: TBD): hosted by authors with restricted access ([request link](https://forms.gle/oW5fwTTZfZcTkp8v9))
- [TWEETSUMM](https://aclanthology.org/2020.coling-main.504/) (language: en, tasks: extractive summarisation, abstractive summarisation): raw data hosted via [Kaggle](https://www.kaggle.com/datasets/thoughtvector/customer-support-on-twitter), annotations hosted via [GitHub](https://github.com/guyfe/Tweetsumm?tab=readme-ov-file)

Directory structure:
```
  |- data/
    |- retrieval/
      |- {corpus_id}/
        |- docs/
          |- data.csv
          |- data_chunked.csv
        |- index/
          |- data/
            |- (lexical index data)
            |- embeddings_cache_{biencoder_model_id}[_normalised].pbz2
            |- embeddings_hnswlib_{configs_hash}_{biencoder_model_id}.index
          |- data_chunked/
            |- (lexical index data)
            |- embeddings_cache_{biencoder_model_id}[_normalised].pbz2
            |- embeddings_hnswlib_{configs_hash}_{biencoder_model_id}.index
      |- ...
    |- cache/
      |- {corpus_id}_{split}_{configs_hash}.pbz2
      |- ...
    |- preprocessed/
      |- {corpus_id}_{split}.csv
      |- {corpus_id}_metadata.yml
      |- ...
    |- raw/
      |- {corpus_id}
        |- ...
      |- ...
```