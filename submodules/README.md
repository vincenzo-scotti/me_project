# Submodules

Hereafter, we describe the submodules used in this repository:
- [LLM CSTK](https://github.com/vincenzo-scotti/llm_cstk) (currently is the only included submodule) 

## LLM CSTK

In this section we describe how to combine the low-level LLM CSTK APIs to build high-level functionalities.
We consider the following applications:

- [Search engine](#search-engine);
- [Similar documents search](#similar-documents-search);
- [Document information extraction](#document-information-extraction);
- [Question answering](#question-answering);
- [Response suggestion](#response-suggestion-1).

### Search engine

To build a search engine using the APIs the passages are the following:

1. Get the query or question from the user;
2. Use the document search functionality to retrieve the IDs of documents relevant to the query (use the chunked search for better results);
3. Paginate the results (e.g., group them into pages of 8 elements);
4. When a page of the results is requested use snippet generation functionality to decorate the results with a snippet of the document (the most relevant to the query).

### Similar documents search

To search for documents relevant to a reference document the passages are the following:

1. Chunk the document into pieces. In the data preparation the default chunking approach is the following:
   1. Create one chunk with the "metadata" of the document (generic information on the content);
   2. Create all the other chunks taking three consecutive turns (speaker-utterance pairs) and move forward by two turns in the sequence (i.e., sliding window of 3 with a stride of 2);
   3. Prepend to each chunk the title of the document.
2. Use the document search with long queries functionality to retrieve the IDs of documents relevant to the current one (use the chunked search for better results);
3. Paginate the results (e.g., group them into pages of 8 elements);
4. When a page of the results is requested use snippet generation functionality to decorate the results with a snippet of the document (the most relevant to the reference document).

### Document information extraction

To extract information from a document prepended to an interactive chat the passages are the following:

1. Convert the document into a single string of text. In the data preparation the default string conversion approach is the following:
   1. Take the title of the document (usually the ticket description or the customer complaint);
   2. Concatenate the metadata of the document (the info of the document);
   3. Concatenate all the turns in the dialogue.
2. Gather all the data from the current chat:
   1. Take the chat metadata (info);
   2. Take the list of the turns up to the current moment in the chat.
3. Use the information extraction functionality passing the metadata of the current chat, the turns of the current and reference document to get a response to the latest user message.

### Question answering

To answer a query given to the search engine the passages are the following:

1. Use the query recognition functionality to understand whether the query to the search engine was in the form of a question or not (stop if it is not);
2. Use the document passage search functionality to search for possibly relevant document using the question from the previous step as query. Keep only the top *k* documents;
3. Use the relevant documents selection functionality to select which of the top *k* documents from the previous steps are useful to answer the question. *Alternatively*, use the semantic re-ranking with a [cross-encoder](https://www.sbert.net/docs/pretrained_cross-encoders.html) trained on information-retrieval data and a threshold ($> 0.5$ for example) on the output score the document passage search functionality from the previous step;
4. Use the knowledge-based question answering functionality to answer the question given the selected documents from the previous step.

#### Response suggestion

There are two ways to get a response suggestion.
Either use a LLM with few-shot learning or use a fine-tuned (custom) (L)LM.

#### LLMs

To get a response suggestion using LLMs the passages are the following: 

1. Search for relevant documents similar to the current chat;
   1. Chunk the document into pieces using the same approach described in [Similar documents search](#similar-documents-search);
   2. Use the document search with long queries functionality to retrieve the IDs of documents relevant to the current chat (use the chunked search for better results);
   3. Extract the metadata and the turns of the most relevant chats (e.g., take the first four);
2. Gather all the data from the current chat:
   1. Take the chat metadata (info);
   2. Take the list of the turns up to the current moment in the chat.
3. Use the response suggestion with LLM functionality passing the metadata of the current chat, the turns of the current and retrieved examples (the examples are necessary for few-shots learning).

#### Custom (L)LMs

In this case it is sufficient to use the response suggestion with custom (L)LM functionality.
