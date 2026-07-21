# Day 11 Chunking Experiment Findings

## Results Table
strategy,chunks,avg_chunk_size,questions_answered,accuracy
fixed_500_no_overlap,95,382,8,8/9
fixed_500_overlap_100,100,396,8,8/9
small_200_overlap_50,268,141,8,8/9
heading_aware_md,25,305,2,2/9

## Key Findings

### 1. Accuracy was identical across three strategies (8/9)
...write why you think this happened...

### 2. Small chunks cost 3x more with no accuracy benefit
268 chunks at 141 chars vs 95 chunks at 382 chars — same 8/9 score.
...write what this means for production cost...

### 3. heading_aware_md answered only 2/9
...write why — it only processed markdown files...
...write when you WOULD use it (pure markdown knowledge base)...

### 4. The one failed question across all strategies
Question: [write which one]
Reason: [write why keyword matching failed on it]
This will be fixed by semantic search on Day 12.

## Winning Strategy
fixed_500_no_overlap — 95 chunks, 382 avg chars, 8/9 accuracy, lowest embedding cost.

## What Changes on Day 12
The one failed question expects semantic search (embeddings) to fix it.
Keyword overlap fails when query vocabulary differs from document vocabulary.