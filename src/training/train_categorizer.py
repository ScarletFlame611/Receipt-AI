# Обучение категоризатора трат
from __future__ import annotations

from pathlib import Path

import numpy as np


def _build_label_maps(labels):
    label2id = {label: i for i, label in enumerate(labels)}
    id2label = {i: label for i, label in enumerate(labels)}
    return label2id, id2label


def _encode_split(rows, tokenizer, label2id, max_length):
    from datasets import Dataset
    texts = [r["text"] for r in rows]
    label_ids = [label2id[r["label"]] for r in rows]
    ds = Dataset.from_dict({"text": texts, "labels": label_ids})

    def tok(batch):
        return tokenizer(batch["text"], truncation=True, max_length=max_length)

    return ds.map(tok, batched=True, remove_columns=["text"])


def _compute_metrics(eval_pred):
    from sklearn.metrics import accuracy_score, f1_score
    logits, labels = eval_pred
    preds = np.argmax(logits, axis=-1)
    return {
        "accuracy": accuracy_score(labels, preds),
        "macro_f1": f1_score(labels, preds, average="macro"),
    }


def train_categorizer(
        data,
        labels,
        base_model="bert-base-multilingual-cased",
        output_dir="runs/categorizer",
        max_length=128,
        epochs=10,
        batch_size=16,
        lr=2e-5,
        weight_decay=0.01,
        fp16=True,
):
    from transformers import (
        AutoModelForSequenceClassification,
        AutoTokenizer,
        DataCollatorWithPadding,
        Trainer,
        TrainingArguments,
    )

    label2id, id2label = _build_label_maps(labels)
    tokenizer = AutoTokenizer.from_pretrained(base_model)

    train_ds = _encode_split(data["train"], tokenizer, label2id, max_length)
    val_ds = _encode_split(data["validation"], tokenizer, label2id, max_length)

    model = AutoModelForSequenceClassification.from_pretrained(
        base_model,
        num_labels=len(labels),
        label2id=label2id,
        id2label=id2label,
    )

    args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=epochs,
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=batch_size,
        learning_rate=lr,
        weight_decay=weight_decay,
        fp16=fp16,
        eval_strategy="epoch",
        save_strategy="epoch",
        save_total_limit=2,
        load_best_model_at_end=True,
        metric_for_best_model="macro_f1",
        greater_is_better=True,
        logging_steps=25,
        report_to="none",
    )

    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=train_ds,
        eval_dataset=val_ds,
        tokenizer=tokenizer,
        data_collator=DataCollatorWithPadding(tokenizer),
        compute_metrics=_compute_metrics,
    )
    trainer.train()
    return trainer, tokenizer


def evaluate_on_test(trainer, data, labels, max_length=128):
    from sklearn.metrics import classification_report
    tokenizer = trainer.tokenizer
    label2id, _ = _build_label_maps(labels)
    test_ds = _encode_split(data["test"], tokenizer, label2id, max_length)
    pred = trainer.predict(test_ds)
    preds = np.argmax(pred.predictions, axis=-1)
    report = classification_report(
        pred.label_ids, preds, target_names=labels, digits=3, output_dict=False
    )
    return report, pred


def save_model(trainer, tokenizer, save_dir):
    Path(save_dir).mkdir(parents=True, exist_ok=True)
    trainer.save_model(save_dir)
    tokenizer.save_pretrained(save_dir)
    return save_dir
