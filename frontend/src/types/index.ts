export interface User {
  id: number;
  username: string;
  role: 'ADMIN' | 'INVESTIGATOR' | 'ANALYST' | 'VIEWER';
  created_at: string;
}

export interface CriminalHistoryItem {
  record_id?: string;
  offense?: string;
  sections?: string;
  disposition?: string;
  case_number?: string;
  jurisdiction?: string;
  date?: string;
  modus_operandi?: string;
}

export interface Entity {
  id: string;
  type: 'PERSON' | 'PHONE' | 'VEHICLE' | 'LOCATION' | 'ORGANIZATION' | 'BANK_ACCOUNT' | 'EVENT' | 'DOCUMENT';
  display_name: string;
  source_type?: string;
  metadata_json: Record<string, any>;
  confidence: number;
  source_document_id?: number;
  created_at?: string;
}

export interface Relationship {
  id: string;
  source_entity_id: string;
  target_entity_id: string;
  type: string;
  source_type?: string;
  timestamp?: string;
  confidence: number;
  source_document_id?: number;
  metadata_json?: Record<string, any>;
}

export interface Alert {
  id: number;
  severity: 'HIGH' | 'MEDIUM' | 'LOW' | 'INFO';
  title: string;
  reason: string;
  evidence_json: any[];
  status: string;
  timestamp: string;
  entity_id?: string;
}

export interface Evidence {
  id: number;
  type: string;
  source_type?: string;
  description: string;
  source_document_id?: number;
  source_document_name?: string;
  entity_id?: string;
  relationship_id?: string;
  created_at: string;
}

export interface TimelineItem {
  timestamp: string;
  description: string;
  evidence_ref: string;
}

export type NetworkScope = 'case' | 'direct' | '2hop' | 'full';

export interface GraphNode {
  id: string;
  type: string;
  display_name: string;
  is_case_entity?: boolean;
  hop_distance?: number;
  properties: Record<string, any>;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  type: string;
  confidence?: number;
  properties: Record<string, any>;
}

export interface InvestigationNetwork {
  investigation_id: string;
  scope: NetworkScope;
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface RiskEntity {
  entity_id: string;
  relationship_count: number;
  average_anomaly_score: number;
  maximum_anomaly_score: number;
  average_confidence: number;
  risk_score: number;
  risk_level: 'HIGH' | 'MEDIUM' | 'LOW';
}

export interface FullGraph {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface CentralityMetric {
  entity_id: string;
  display_name: string;
  type: string;
  influence_score: number;
  betweenness_score: number;
  degree_score: number;
  closeness_score: number;
}

export interface Investigation {
  id: string;
  title: string;
  description?: string;
  created_by: string;
  created_date: string;
  status: 'Active' | 'Suspended' | 'Closed';
  priority: 'High' | 'Medium' | 'Low';
  entities_json: string[];
  notes?: string;
}

export interface EntityResolution {
  id: number;
  source_entity_id: string;
  source_display_name: string;
  target_entity_id: string;
  target_display_name: string;
  confidence: number;
  status: 'PENDING' | 'MERGED' | 'REJECTED';
  created_at: string;
}

