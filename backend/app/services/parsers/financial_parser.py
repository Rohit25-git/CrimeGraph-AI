import csv
import io
import json
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List

from backend.app.services.parsers.base_parser import (
    BaseSourceParser,
    ExtractedEntity,
    ExtractedRelationship,
    ExtractedEvidence,
    ParsedSourceResult
)

logger = logging.getLogger("financial_parser")

class FinancialTransactionParser(BaseSourceParser):
    """Parser for Financial Transaction Records, Bank Statements, and Payment Logs."""

    @property
    def source_type_name(self) -> str:
        return "FINANCIAL"

    def can_parse(self, content: bytes, filename: str) -> bool:
        fn_lower = filename.lower()
        if any(w in fn_lower for w in ["bank", "txn", "transact", "financial", "ledger", "statement", "payment", "wire"]):
            return True
        try:
            sample = content[:1024].decode("utf-8", errors="ignore").lower()
            keywords = ["sender_acc", "receiver_acc", "remitter", "beneficiary", "txn_amount", "credit_acc", "debit_acc", "ifsc"]
            return any(kw in sample for kw in keywords)
        except Exception:
            return False

    def parse(self, content: bytes, filename: str, metadata: Optional[Dict[str, Any]] = None) -> ParsedSourceResult:
        text = content.decode("utf-8", errors="ignore")
        records: List[Dict[str, Any]] = []

        if filename.lower().endswith(".json"):
            try:
                data = json.loads(text)
                records = data if isinstance(data, list) else [data]
            except Exception as e:
                logger.warning(f"Failed to parse Financial JSON: {e}")
        else:
            try:
                reader = csv.DictReader(io.StringIO(text))
                records = [row for row in reader]
            except Exception as e:
                logger.warning(f"Failed to parse Financial CSV: {e}")

        entities_map: Dict[str, ExtractedEntity] = {}
        relationships: List[ExtractedRelationship] = []
        evidence_list: List[ExtractedEvidence] = []

        for row in records:
            norm_row = {k.strip().lower(): str(v).strip() for k, v in row.items() if k and v is not None}

            sender_acc = (norm_row.get("sender_acc") or norm_row.get("source_acc") or 
                          norm_row.get("from_account") or norm_row.get("sender_account") or 
                          norm_row.get("remitter_acc") or norm_row.get("debit_acc") or "")

            receiver_acc = (norm_row.get("receiver_acc") or norm_row.get("target_acc") or 
                            norm_row.get("to_account") or norm_row.get("beneficiary_acc") or 
                            norm_row.get("credit_acc") or norm_row.get("receiver_account") or "")

            if not sender_acc or not receiver_acc:
                continue

            sender_acc_id = sender_acc if sender_acc.startswith("ACC") else f"ACC_{sender_acc.replace('-', '')}"
            receiver_acc_id = receiver_acc if receiver_acc.startswith("ACC") else f"ACC_{receiver_acc.replace('-', '')}"

            sender_name = norm_row.get("sender_name") or norm_row.get("remitter_name") or norm_row.get("source_owner") or ""
            receiver_name = norm_row.get("receiver_name") or norm_row.get("beneficiary_name") or norm_row.get("target_owner") or ""

            amt_str = norm_row.get("amount") or norm_row.get("txn_amount") or norm_row.get("transaction_amount") or norm_row.get("value") or "0"
            try:
                amount = float(amt_str.replace(",", "").replace("$", "").replace("₹", ""))
            except ValueError:
                amount = 0.0

            currency = norm_row.get("currency") or "INR"
            txn_type = norm_row.get("txn_type") or norm_row.get("type") or norm_row.get("channel") or "IMPS"
            bank_name = norm_row.get("bank_name") or norm_row.get("bank") or ""

            # Timestamp parsing
            ts_str = (norm_row.get("timestamp") or norm_row.get("txn_date") or 
                      norm_row.get("date") or norm_row.get("transaction_date") or "")
            ts = None
            if ts_str:
                for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
                    try:
                        ts = datetime.strptime(ts_str, fmt)
                        break
                    except ValueError:
                        pass
            if not ts:
                ts = datetime.utcnow()

            # 1. Sender Bank Account Entity
            if sender_acc_id not in entities_map:
                entities_map[sender_acc_id] = ExtractedEntity(
                    id=sender_acc_id,
                    type="BANK_ACCOUNT",
                    display_name=f"Account {sender_acc}",
                    confidence=1.0,
                    properties={"raw_account": sender_acc, "owner": sender_name, "bank": bank_name},
                    source_type="FINANCIAL"
                )

            # 2. Receiver Bank Account Entity
            if receiver_acc_id not in entities_map:
                entities_map[receiver_acc_id] = ExtractedEntity(
                    id=receiver_acc_id,
                    type="BANK_ACCOUNT",
                    display_name=f"Account {receiver_acc}",
                    confidence=1.0,
                    properties={"raw_account": receiver_acc, "owner": receiver_name},
                    source_type="FINANCIAL"
                )

            # 3. Person entities if owners identified
            if sender_name:
                p_sender_id = f"P_{sender_name.replace(' ', '_')}"
                if p_sender_id not in entities_map:
                    entities_map[p_sender_id] = ExtractedEntity(
                        id=p_sender_id,
                        type="PERSON",
                        display_name=sender_name,
                        confidence=0.95,
                        properties={"bank_account": sender_acc},
                        source_type="FINANCIAL"
                    )
                relationships.append(ExtractedRelationship(
                    source_entity_id=p_sender_id,
                    target_entity_id=sender_acc_id,
                    type="OWNS",
                    timestamp=ts,
                    confidence=0.95,
                    properties={"financial_record": True},
                    source_type="FINANCIAL",
                    id=str(uuid.uuid4())
                ))

            if receiver_name:
                p_receiver_id = f"P_{receiver_name.replace(' ', '_')}"
                if p_receiver_id not in entities_map:
                    entities_map[p_receiver_id] = ExtractedEntity(
                        id=p_receiver_id,
                        type="PERSON",
                        display_name=receiver_name,
                        confidence=0.95,
                        properties={"bank_account": receiver_acc},
                        source_type="FINANCIAL"
                    )
                relationships.append(ExtractedRelationship(
                    source_entity_id=p_receiver_id,
                    target_entity_id=receiver_acc_id,
                    type="OWNS",
                    timestamp=ts,
                    confidence=0.95,
                    properties={"financial_record": True},
                    source_type="FINANCIAL",
                    id=str(uuid.uuid4())
                ))

            # 4. Transfer relationship between accounts
            rel_id = str(uuid.uuid4())
            relationships.append(ExtractedRelationship(
                source_entity_id=sender_acc_id,
                target_entity_id=receiver_acc_id,
                type="TRANSFERRED_TO",
                timestamp=ts,
                confidence=1.0,
                properties={
                    "amount": amount,
                    "currency": currency,
                    "txn_type": txn_type,
                    "bank": bank_name
                },
                source_type="FINANCIAL",
                id=rel_id
            ))

            # If both persons exist, also add direct financial relation between persons
            if sender_name and receiver_name:
                p_sender_id = f"P_{sender_name.replace(' ', '_')}"
                p_receiver_id = f"P_{receiver_name.replace(' ', '_')}"
                relationships.append(ExtractedRelationship(
                    source_entity_id=p_sender_id,
                    target_entity_id=p_receiver_id,
                    type="TRANSFERRED_TO",
                    timestamp=ts,
                    confidence=0.9,
                    properties={"amount": amount, "via_account": sender_acc},
                    source_type="FINANCIAL",
                    id=str(uuid.uuid4())
                ))

            # 5. Evidence
            evidence_list.append(ExtractedEvidence(
                type="TRANSACTION",
                description=f"Financial wire: {sender_name or sender_acc} transferred {currency} {amount:,.2f} to {receiver_name or receiver_acc} via {txn_type} on {ts.strftime('%Y-%m-%d')}.",
                source_type="FINANCIAL",
                relationship_id=rel_id,
                properties={"amount": amount, "currency": currency, "sender": sender_acc, "receiver": receiver_acc}
            ))

        summary = f"Financial statement parsed from {filename}: {len(records)} transactions, {len(entities_map)} entities, {len(relationships)} transfers mapped."
        return ParsedSourceResult(
            source_type="FINANCIAL",
            text_summary=summary,
            entities=list(entities_map.values()),
            relationships=relationships,
            evidence=evidence_list,
            raw_records=records
        )
