import logging
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import networkx as nx
import numpy as np
from typing import List, Dict, Any

from backend.app.models.database_models import Relationship, Entity, Alert
from backend.app.services.graph_service import GraphService

logger = logging.getLogger("anomaly_service")

class AnomalyService:
    @staticmethod
    def detect_all_anomalies(db: Session) -> int:
        """Runs all anomaly detection algorithms and inserts new alerts. Returns count of new alerts."""
        new_alerts_count = 0
        
        # Clear old alerts to avoid duplicates for the demo
        db.query(Alert).delete()
        db.commit()
        
        # 1. Circular Transactions
        new_alerts_count += AnomalyService.detect_circular_transactions(db)
        
        # 2. Financial Value Outliers
        new_alerts_count += AnomalyService.detect_financial_outliers(db)
        
        # 3. Communication Spikes
        new_alerts_count += AnomalyService.detect_communication_spikes(db)
        
        # 4. Cross-Community Connections
        new_alerts_count += AnomalyService.detect_cross_community_bridges(db)
        
        # 5. Location Overlaps
        new_alerts_count += AnomalyService.detect_location_overlaps(db)

        # 6. Rapid Network Expansion
        new_alerts_count += AnomalyService.detect_rapid_expansions(db)

        # 7. Temporal Anomalies
        new_alerts_count += AnomalyService.detect_temporal_anomalies(db)
        
        return new_alerts_count

    @staticmethod
    def detect_circular_transactions(db: Session) -> int:
        """Finds loops like A -> B -> C -> A in financial relationships."""
        # Get all financial relationships (TRANSFERRED_TO)
        rels = db.query(Relationship).filter(Relationship.type == "TRANSFERRED_TO").all()
        
        G = nx.DiGraph()
        # Map of (u, v) -> relationship record for evidence lookup
        rel_map = {}
        for r in rels:
            G.add_edge(r.source_entity_id, r.target_entity_id)
            rel_map[(r.source_entity_id, r.target_entity_id)] = r
            
        try:
            cycles = list(nx.simple_cycles(G))
        except Exception as e:
            logger.error(f"Error in cycle detection: {e}")
            cycles = []
            
        alert_count = 0
        for cycle in cycles:
            if len(cycle) < 2:
                continue
                
            # Create descriptive text
            cycle_str = " -> ".join(cycle) + " -> " + cycle[0]
            reason = f"A circular financial flow was detected: {cycle_str}. This pattern requires review as it might indicate funds cycling."
            
            # Evidence list
            evidence = []
            for i in range(len(cycle)):
                u = cycle[i]
                v = cycle[(i + 1) % len(cycle)]
                r = rel_map.get((u, v))
                if r:
                    evidence.append({
                        "relationship_id": r.id,
                        "from": u,
                        "to": v,
                        "amount": r.metadata_json.get("amount", 0),
                        "timestamp": r.timestamp.isoformat() if r.timestamp else None
                    })
                    
            # Primary entity is the first node in the cycle
            primary_entity = cycle[0]
            
            alert = Alert(
                severity="HIGH",
                title="Circular Financial Transaction Pattern",
                reason=reason,
                evidence_json=evidence,
                status="Requires Human Review",
                entity_id=primary_entity,
                timestamp=datetime.utcnow()
            )
            db.add(alert)
            alert_count += 1
            
        db.commit()
        return alert_count

    @staticmethod
    def detect_financial_outliers(db: Session) -> int:
        """Flags transactions that are statistically higher than normal (> mean + 2*std)."""
        rels = db.query(Relationship).filter(Relationship.type == "TRANSFERRED_TO").all()
        if not rels:
            return 0
            
        amounts = [float(r.metadata_json.get("amount", 0)) for r in rels if "amount" in r.metadata_json]
        if len(amounts) < 5:  # Not enough data for statistics
            return 0
            
        mean = np.mean(amounts)
        std = np.std(amounts)
        threshold = mean + 2.0 * std  # Statistical threshold
        
        alert_count = 0
        for r in rels:
            amt = float(r.metadata_json.get("amount", 0))
            if amt > threshold and amt > 10000:  # Ignore trivial transactions
                reason = f"Transaction from {r.source_entity_id} to {r.target_entity_id} of amount INR {amt:,.2f} is significantly above the network transaction average of INR {mean:,.2f} (Threshold: INR {threshold:,.2f})."
                
                evidence = [{
                    "relationship_id": r.id,
                    "amount": amt,
                    "average": round(mean, 2),
                    "timestamp": r.timestamp.isoformat() if r.timestamp else None
                }]
                
                alert = Alert(
                    severity="HIGH",
                    title="High-Value Transaction Anomaly",
                    reason=reason,
                    evidence_json=evidence,
                    status="Requires Human Review",
                    entity_id=r.source_entity_id,
                    timestamp=datetime.utcnow()
                )
                db.add(alert)
                alert_count += 1
                
        db.commit()
        return alert_count

    @staticmethod
    def detect_communication_spikes(db: Session) -> int:
        """Flags entities with unusually high volume of calls in a short window."""
        calls = db.query(Relationship).filter(Relationship.type.in_(["CALLED", "MESSAGED"])).all()
        if not calls:
            return 0
            
        # Group by sender and date
        counts = {}
        for c in calls:
            if not c.timestamp:
                continue
            date_str = c.timestamp.date().isoformat()
            sender = c.source_entity_id
            
            key = (sender, date_str)
            counts[key] = counts.get(key, []) + [c]
            
        alert_count = 0
        # Trigger spike alert if an entity makes > 5 calls/messages to unique numbers in a single day
        for (sender, date_str), rel_list in counts.items():
            unique_recipients = len(set(r.target_entity_id for r in rel_list))
            if len(rel_list) >= 8:  # 8 or more interactions in a single day
                reason = f"Entity {sender} showed a communication spike on {date_str} with {len(rel_list)} outgoing communications (calls/messages) to {unique_recipients} unique entities. This represents a substantial deviation from normal baseline activity."
                
                evidence = [{
                    "relationship_id": r.id,
                    "recipient": r.target_entity_id,
                    "type": r.type,
                    "timestamp": r.timestamp.isoformat() if r.timestamp else None
                } for r in rel_list]
                
                alert = Alert(
                    severity="MEDIUM",
                    title="Sudden Communication Spike",
                    reason=reason,
                    evidence_json=evidence,
                    status="Requires Human Review",
                    entity_id=sender,
                    timestamp=datetime.utcnow()
                )
                db.add(alert)
                alert_count += 1
                
        db.commit()
        return alert_count

    @staticmethod
    def detect_cross_community_bridges(db: Session) -> int:
        """Flags nodes that connect different communities (structural bridges)."""
        communities = GraphService.detect_communities(db)
        if not communities:
            return 0
            
        # For each entity, count how many different communities it connects to
        rels = db.query(Relationship).all()
        connections = {}
        for r in rels:
            s, t = r.source_entity_id, r.target_entity_id
            if s not in connections:
                connections[s] = set()
            if t not in connections:
                connections[t] = set()
                
            s_comm = communities.get(s)
            t_comm = communities.get(t)
            
            if s_comm is not None:
                connections[t].add(s_comm)
            if t_comm is not None:
                connections[s].add(t_comm)
                
        alert_count = 0
        for ent_id, connected_comms in connections.items():
            # If an entity is connected to 3 or more distinct communities, it is a cross-community bridge
            if len(connected_comms) >= 3:
                ent = db.query(Entity).filter(Entity.id == ent_id).first()
                if not ent:
                    continue
                    
                reason = f"Entity {ent.display_name} ({ent_id}) acts as a structural bridge connecting {len(connected_comms)} distinct network communities. Bridge nodes are key operational points linking separate clusters."
                
                evidence = [{
                    "entity_id": ent_id,
                    "connected_communities_count": len(connected_comms),
                    "detected_community_id": communities.get(ent_id)
                }]
                
                alert = Alert(
                    severity="MEDIUM",
                    title="Cross-Community Network Bridge",
                    reason=reason,
                    evidence_json=evidence,
                    status="Requires Human Review",
                    entity_id=ent_id,
                    timestamp=datetime.utcnow()
                )
                db.add(alert)
                alert_count += 1
                
        db.commit()
        return alert_count

    @staticmethod
    def detect_location_overlaps(db: Session) -> int:
        """Detects if multiple persons appear at the same location within a 2-hour window."""
        # Find all VISITED / MET location relationships
        rels = db.query(Relationship).filter(Relationship.type == "VISITED").all()
        if not rels:
            return 0
            
        # Group visits by location
        location_visits = {}
        for r in rels:
            loc_id = r.target_entity_id
            if not r.timestamp:
                continue
            if loc_id not in location_visits:
                location_visits[loc_id] = []
            location_visits[loc_id].append(r)
            
        alert_count = 0
        for loc_id, visits in location_visits.items():
            # Sort visits by timestamp
            visits.sort(key=lambda x: x.timestamp)
            
            # Find pairs within 2 hours
            for i in range(len(visits)):
                for j in range(i + 1, len(visits)):
                    v1 = visits[i]
                    v2 = visits[j]
                    
                    if v1.source_entity_id == v2.source_entity_id:
                        continue  # Same person visiting twice
                        
                    time_diff = abs(v1.timestamp - v2.timestamp)
                    if time_diff <= timedelta(hours=2):
                        reason = f"Repeated spatial-temporal overlap: {v1.source_entity_id} and {v2.source_entity_id} visited Location {loc_id} within {time_diff.seconds//60} minutes of each other (Visit 1: {v1.timestamp.strftime('%H:%M')}, Visit 2: {v2.timestamp.strftime('%H:%M')})."
                        
                        evidence = [
                            {
                                "relationship_id": v1.id,
                                "entity_id": v1.source_entity_id,
                                "timestamp": v1.timestamp.isoformat()
                            },
                            {
                                "relationship_id": v2.id,
                                "entity_id": v2.source_entity_id,
                                "timestamp": v2.timestamp.isoformat()
                            }
                        ]
                        
                        # Raise alert for v1 (the first visitor)
                        alert = Alert(
                            severity="MEDIUM",
                            title="Location Overlap Anomaly",
                            reason=reason,
                            evidence_json=evidence,
                            status="Requires Human Review",
                            entity_id=v1.source_entity_id,
                            timestamp=datetime.utcnow()
                        )
                        db.add(alert)
                        alert_count += 1
                        
        db.commit()
        return alert_count

    @staticmethod
    def detect_rapid_expansions(db: Session) -> int:
        """Flags entities establishing 5+ new unique links within a rolling 3-day window."""
        rels = db.query(Relationship).all()
        if not rels:
            return 0

        # Group relationships by source entity
        connections = {}
        for r in rels:
            if not r.timestamp:
                continue
            src = r.source_entity_id
            if src not in connections:
                connections[src] = []
            connections[src].append((r.timestamp, r))

        alert_count = 0
        for src_id, items in connections.items():
            items.sort(key=lambda x: x[0])  # Sort by timestamp
            for i in range(len(items)):
                window_start = items[i][0]
                window_end = window_start + timedelta(days=3)
                
                # Count relationships in this 3-day window
                window_rels = [item[1] for item in items[i:] if item[0] <= window_end]
                unique_targets = len(set(r.target_entity_id for r in window_rels))
                
                if unique_targets >= 6:  # 6 or more targets in a 3-day window is rapid expansion
                    reason = f"Rapid network expansion: Entity {src_id} established connections with {unique_targets} unique target nodes within a 72-hour window. This sudden clustering indicates an operational spike."
                    
                    evidence = [{
                        "relationship_id": r.id,
                        "target_entity": r.target_entity_id,
                        "type": r.type,
                        "timestamp": r.timestamp.isoformat()
                    } for r in window_rels]
                    
                    alert = Alert(
                        severity="HIGH",
                        title="Rapid Network Expansion Anomaly",
                        reason=reason,
                        evidence_json=evidence,
                        status="Requires Human Review",
                        entity_id=src_id,
                        timestamp=datetime.utcnow()
                    )
                    db.add(alert)
                    alert_count += 1
                    break  # Alert once per entity to prevent spamming
                    
        db.commit()
        return alert_count

    @staticmethod
    def detect_temporal_anomalies(db: Session) -> int:
        """Flags transactions or communications occurring during unusual hours (1 AM to 4 AM)."""
        # Look for relationships during night hours
        rels = db.query(Relationship).all()
        alert_count = 0
        for r in rels:
            if not r.timestamp:
                continue
            # Check if hour is between 1 and 4 AM (unusual operation hour)
            hour = r.timestamp.hour
            if 1 <= hour <= 4:
                reason = f"Unusual temporal activity: A {r.type} link was established between {r.source_entity_id} and {r.target_entity_id} at {r.timestamp.strftime('%H:%M:%S')} (night-time window). Operational activity during sleep hours represents a potential anomaly."
                
                evidence = [{
                    "relationship_id": r.id,
                    "type": r.type,
                    "timestamp": r.timestamp.isoformat(),
                    "hour": hour
                }]
                
                alert = Alert(
                    severity="LOW",
                    title="Unusual Temporal Activity Alert",
                    reason=reason,
                    evidence_json=evidence,
                    status="Requires Human Review",
                    entity_id=r.source_entity_id,
                    timestamp=datetime.utcnow()
                )
                db.add(alert)
                alert_count += 1
                
        db.commit()
        return alert_count

