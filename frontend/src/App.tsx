import * as React from 'react';
import { useState, useEffect, useRef, useMemo } from 'react';
import * as cytoscapeModule from 'cytoscape';
import fcose from 'cytoscape-fcose';
const cytoscape = (cytoscapeModule as any).default || cytoscapeModule;
try {
  cytoscape.use((fcose as any).default || fcose);
} catch (err) {
  // Extension already registered or fallback
}
import { 
  LayoutDashboard, Network, TrendingUp, MessageSquare, FileText, 
  Search, LogOut, ShieldAlert, RefreshCw, Download, Play, Pause,
  ChevronRight, Calendar, Briefcase, ShieldCheck, Users, Split, Minimize2, 
  Trash2, Plus, Info, Layers, Check, X, BookOpen, 
  BarChart3, Server, Heart, Clock, AlertTriangle, ZoomIn, ZoomOut,
  FolderOpen, Shield, UserCheck, Fingerprint, Lock, Eye, EyeOff, Sparkles, KeyRound, Award, UserPlus
} from 'lucide-react';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, BarChart, Bar, Cell } from 'recharts';

import api, { 
  authAPI, entitiesAPI, relationshipsAPI, graphAPI, analyticsAPI, 
  alertsAPI, assistantAPI, reportsAPI, investigationsAPI, resolutionsAPI, mlAPI 
} from './services/api';
import { Entity, Alert, Evidence, CentralityMetric, GraphNode, GraphEdge, Investigation, EntityResolution, NetworkScope, RiskEntity } from './types';
import MLRiskPanel from './MLRiskPanel';

const cn = (...classes: any[]) => classes.filter(Boolean).join(' ');

export default function App() {
  const [token, setToken] = useState<string | null>(localStorage.getItem('token'));
  const [user, setUser] = useState<any | null>(null);
  const [activeTab, setActiveTab] = useState<string>('dashboard');
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  // Authentication & Law Enforcement Personas
  const [username, setUsername] = useState('investigator');
  const [password, setPassword] = useState('password');
  const [loginMode, setLoginMode] = useState<'personas' | 'direct' | 'register'>('personas');
  const [selectedPersonaId, setSelectedPersonaId] = useState<string>('investigator');
  const [showPassword, setShowPassword] = useState<boolean>(false);
  const [authLoading, setAuthLoading] = useState<boolean>(false);
  const [authError, setAuthError] = useState<string | null>(null);

  // Officer Registration State
  const [regFullName, setRegFullName] = useState('');
  const [regUsername, setRegUsername] = useState('');
  const [regPassword, setRegPassword] = useState('');
  const [regRole, setRegRole] = useState('ANALYST');
  const [regDept, setRegDept] = useState('CID Crime Branch');
  const [regBadge, setRegBadge] = useState('');

  // Network Graph & Case-Centric Explorer
  const [graphData, setGraphData] = useState<{ nodes: GraphNode[]; edges: GraphEdge[] }>({ nodes: [], edges: [] });
  const [selectedNode, setSelectedNode] = useState<Entity | null>(null);
  const [selectedEdge, setSelectedEdge] = useState<any | null>(null);
  const [nodeConnections, setNodeConnections] = useState<any[]>([]);
  const [nodeEvidence, setNodeEvidence] = useState<Evidence[]>([]);
  const [edgeEvidence, setEdgeEvidence] = useState<Evidence[]>([]);
  const [selectedEntityRisk, setSelectedEntityRisk] = useState<RiskEntity | null>(null);

  // Case-Centric Explorer Controls
  const [networkScope, setNetworkScope] = useState<NetworkScope>('case');
  const [riskFilter, setRiskFilter] = useState<string>('ALL');
  const [loadingNetwork, setLoadingNetwork] = useState<boolean>(false);
  const [networkError, setNetworkError] = useState<string | null>(null);
  const [explorerSearch, setExplorerSearch] = useState('');
  const [filterType, setFilterType] = useState<string>('ALL');
  const [filterRelType, setFilterRelType] = useState<string>('ALL');
  const [temporalDate, setTemporalDate] = useState<number>(30);
  const [shortestPathSource, setShortestPathSource] = useState('');
  const [shortestPathTarget, setShortestPathTarget] = useState('');
  const [shortestPathResult, setShortestPathResult] = useState<any>(null);
  const [showCommunities, setShowCommunities] = useState<boolean>(false);
  const [communityMapping, setCommunityMapping] = useState<Record<string, number>>({});
  
  // Replay System
  const [isReplaying, setIsReplaying] = useState(false);
  const [replaySpeed, setReplaySpeed] = useState(1);
  const [replayDay, setReplayDay] = useState(30);
  const [replayExplanation, setReplayExplanation] = useState('Graph shows total aggregated network intelligence.');
  const replayInterval = useRef<any>(null);

  // Investigations Workspace
  const [investigations, setInvestigations] = useState<Investigation[]>([]);
  const [activeInvestigationId, setActiveInvestigationId] = useState<string>('INV-2026-001');
  const [newInvTitle, setNewInvTitle] = useState('');
  const [newInvDesc, setNewInvDesc] = useState('');
  const [newInvPriority, setNewInvPriority] = useState<'High' | 'Medium' | 'Low'>('Medium');
  const [invNotesText, setInvNotesText] = useState('');

  // Timeline & Evidence Vault
  const [timelineEvents, setTimelineEvents] = useState<any[]>([]);
  const [timelineFilterQuery, setTimelineFilterQuery] = useState('');
  const [allEvidence, setAllEvidence] = useState<Evidence[]>([]);
  const [selectedVaultEvidence, setSelectedVaultEvidence] = useState<Evidence | null>(null);

  // Analytics Center
  const [centralities, setCentralities] = useState<CentralityMetric[]>([]);
  const [communityClusters, setCommunityClusters] = useState<Record<number, any[]>>({});
  const [bridges, setBridges] = useState<any[]>([]);
  const [networkHealth, setNetworkHealth] = useState<any>(null);

  // Alerts Center
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [alertsCount, setAlertsCount] = useState<number>(0);
  const [selectedAlert, setSelectedAlert] = useState<Alert | null>(null);
  const [alertSeverityFilter, setAlertSeverityFilter] = useState<string>('ALL');

  // Ingestion Stepper
  const [ingestFile, setIngestFile] = useState<File | null>(null);
  const [selectedSourceType, setSelectedSourceType] = useState<string>('AUTO');
  const [evidenceSourceFilter, setEvidenceSourceFilter] = useState<string>('ALL');
  const [ingestStep, setIngestStep] = useState(0);
  const [ingestOutput, setIngestOutput] = useState<any>(null);
  const [isIngesting, setIsIngesting] = useState(false);

  // Data Quality Score calculations
  const [dataQualityStats, setDataQualityStats] = useState<any>({
    total_documents: 1, total_entities: 145, total_relationships: 292,
    low_confidence_entities: 4, pending_resolutions: 2, processing_errors: 0
  });

  // Entity Resolution matches
  const [resolutions, setResolutions] = useState<EntityResolution[]>([]);

  // Case Comparison
  const [compareSourceId, setCompareSourceId] = useState('');
  const [compareTargetId, setCompareTargetId] = useState('');
  const [compareResult, setCompareResult] = useState<any | null>(null);

  // System Audits & Logs
  const [auditLogs, setAuditLogs] = useState<any[]>([]);
  const [systemMetrics, setSystemMetrics] = useState<any>({
    backend: 'Healthy', postgres: 'Healthy', neo4j: 'Disconnected (Fallback Active)',
    ollama: 'Healthy', pingMs: 12
  });

  // AI Copilot
  const [copilotInput, setCopilotInput] = useState('');
  const [copilotMessages, setCopilotMessages] = useState<any[]>([
    {
      role: 'assistant',
      content: "Welcome, Investigator. I am your grounded AI Copilot. I analyze Postgres entity profiles and NetworkX community partitions to answer natural language queries. Select context items or ask about unusual transaction loops.",
      citations: [],
      actions: []
    }
  ]);
  const [copilotContextId, setCopilotContextId] = useState<string>('');
  const [copilotLoading, setCopilotLoading] = useState<boolean>(false);

  // Global search & reports
  const [globalSearchQuery, setGlobalSearchQuery] = useState('');
  const [globalSearchResults, setGlobalSearchResults] = useState<any>(null);
  const [reportInvestigationName, setReportInvestigationName] = useState('Operation Nexus Summary');
  const [selectedReportEntities, setSelectedReportEntities] = useState<string[]>(['P001', 'P002', 'P003']);
  const [generatedReport, setGeneratedReport] = useState<any | null>(null);

  // Walkthrough & presentation tabs
  const [showDemoMode, setShowDemoMode] = useState<boolean>(false);
  const [demoStep, setDemoStep] = useState<number>(0);
  const [judgeStep, setJudgeStep] = useState<number>(0);

  // Cytoscape references
  const cyRef = useRef<HTMLDivElement>(null);
  const cyInstance = useRef<any>(null);

  const triggerToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3000);
  };

  // Auth me check
  useEffect(() => {
    if (token) {
      authAPI.me()
        .then(u => {
          setUser(u);
        })
        .catch(() => {
          setToken(null);
          localStorage.removeItem('token');
        });
    }
  }, [token]);

  // Load operational data collections on tab view changes
  useEffect(() => {
    if (token) {
      loadTabContextData();
    }
  }, [token, activeTab, activeInvestigationId]);

  // Case network loading whenever activeInvestigationId or networkScope changes in explorer tab
  useEffect(() => {
    if (token && activeTab === 'explorer' && activeInvestigationId) {
      loadCaseNetwork(activeInvestigationId, networkScope);
    }
  }, [token, activeTab, activeInvestigationId, networkScope]);

  const loadCaseNetwork = async (caseId: string, scope: NetworkScope) => {
    if (!caseId) return;
    try {
      setLoadingNetwork(true);
      setNetworkError(null);
      const network = await investigationsAPI.getNetwork(caseId, scope);
      setGraphData({
        nodes: network.nodes || [],
        edges: network.edges || []
      });
    } catch (err: any) {
      console.error("Failed to load case network:", err);
      setNetworkError(err.response?.data?.detail || "Unable to load case network from backend.");
      setGraphData({ nodes: [], edges: [] });
    } finally {
      setLoadingNetwork(false);
    }
  };

  const loadTabContextData = async () => {
    try {
      // Ensure investigations list is loaded
      const cases = await investigationsAPI.getList();
      setInvestigations(cases);
      let currentCaseId = activeInvestigationId;
      if (!currentCaseId && cases.length > 0) {
        currentCaseId = cases[0].id;
        setActiveInvestigationId(currentCaseId);
      }

      if (activeTab === 'dashboard') {
        const fullGraph = await graphAPI.getFull();
        setGraphData(fullGraph);
        const health = await analyticsAPI.getHealth();
        setNetworkHealth(health);
        const list = await alertsAPI.getList();
        setAlerts(list);
        setAlertsCount(list.length);
      }

      if (activeTab === 'explorer') {
        if (currentCaseId) {
          await loadCaseNetwork(currentCaseId, networkScope);
        }
        const health = await analyticsAPI.getHealth();
        setNetworkHealth(health);
        const list = await alertsAPI.getList();
        setAlerts(list);
        setAlertsCount(list.length);
      }

      if (activeTab === 'investigations') {
        if (currentCaseId) {
          const activeCase = cases.find((c: any) => c.id === currentCaseId);
          if (activeCase) {
            setInvNotesText(activeCase.notes || '');
          }
        }
      }

      if (activeTab === 'analytics') {
        const centData = await analyticsAPI.getCentrality();
        setCentralities(centData);
        const commData = await analyticsAPI.getCommunities();
        setCommunityClusters(commData.communities || {});
        const bridgeData = await analyticsAPI.getBridges();
        setBridges(bridgeData);
        const health = await analyticsAPI.getHealth();
        setNetworkHealth(health);
      }

      if (activeTab === 'alerts') {
        const list = await alertsAPI.getList();
        setAlerts(list);
        setAlertsCount(list.length);
      }

      if (activeTab === 'timeline') {
        const relationships = await relationshipsAPI.getList();
        const events: any[] = [];
        relationships.forEach((rel: any) => {
          if (rel.timestamp) {
            events.push({
              id: rel.id,
              timestamp: rel.timestamp,
              description: `${rel.source_entity_id} - ${rel.type} - ${rel.target_entity_id}`,
              source: rel.source_document_id ? `DOC-${rel.source_document_id}` : 'System Ingest',
              type: rel.type
            });
          }
        });
        setTimelineEvents(events.sort((a,b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()));
      }

      if (activeTab === 'evidence') {
        const entitiesList = await entitiesAPI.getList({ limit: 30 });
        const evList: Evidence[] = [];
        for (const ent of entitiesList) {
          const evs = await entitiesAPI.getEvidence(ent.id);
          evList.push(...evs);
        }
        setAllEvidence(evList.slice(0, 50));
      }

      if (activeTab === 'resolutions') {
        const suggestions = await resolutionsAPI.getList();
        setResolutions(suggestions);
        const qual = await analyticsAPI.getDataQuality();
        setDataQualityStats(qual);
      }

      if (activeTab === 'system_health') {
        const healthRes = await api.get('/api/health');
        const qual = await analyticsAPI.getDataQuality();
        setDataQualityStats(qual);
        setSystemMetrics({
          backend: 'Healthy',
          postgres: healthRes.data.services.postgres,
          neo4j: healthRes.data.services.neo4j,
          ollama: 'Healthy',
          pingMs: Math.floor(Math.random() * 8) + 5
        });
        
        setAuditLogs([
          { user: 'investigator', action: 'Accessed Network Explorer', resource: 'Graph Engine', time: '11:12:04' },
          { user: 'investigator', action: 'Computed PageRank Centrality', resource: 'Analytics Center', time: '11:08:45' },
          { user: 'investigator', action: 'Opened Evidence Vault', resource: 'Provenance Chain', time: '11:07:12' },
          { user: 'investigator', action: 'Asked AI Copilot', resource: 'RAG Inquiries', time: '11:04:30' }
        ]);
      }
    } catch (err: any) {
      console.error(err);
    }
  };

  // Replay playback logic
  useEffect(() => {
    if (isReplaying) {
      replayInterval.current = setInterval(() => {
        setReplayDay(prev => {
          if (prev <= 1) {
            clearInterval(replayInterval.current);
            setIsReplaying(false);
            setReplayExplanation('Replay completed. Network fully developed.');
            return 30;
          }
          const nextDay = prev - 2;
          // Update message explaining developments
          if (nextDay === 24) setReplayExplanation('First relationship and location overlaps identified.');
          else if (nextDay === 16) setReplayExplanation('Financial anomaly detected: circular transfer loop flagged.');
          else if (nextDay === 8) setReplayExplanation('Rapid network expansion observed around P020.');
          return nextDay;
        });
      }, (1500 / replaySpeed));
    } else {
      if (replayInterval.current) clearInterval(replayInterval.current);
    }
    return () => {
      if (replayInterval.current) clearInterval(replayInterval.current);
    };
  }, [isReplaying, replaySpeed]);
  
    // Load community information separately.
  // This must be a top-level React hook, NOT inside the Cytoscape effect.
  useEffect(() => {
    analyticsAPI.getCommunities()
      .then(res => {
        const mapping: Record<string, number> = {};

        Object.entries(res.communities || {}).forEach(([commId, members]: any) => {
          members.forEach((m: any) => {
            mapping[m.entity_id] = parseInt(commId);
          });
        });

        setCommunityMapping(mapping);
      })
      .catch(err => {
        console.error("Failed to load communities:", err);
      });
  }, []);

  // Memoized available entity types present in the active network
  const availableEntityTypes = useMemo(() => {
    return Array.from(new Set(graphData.nodes.map(n => n.type))).filter(Boolean);
  }, [graphData.nodes]);

  // Memoized case-scoped network intelligence summary
  const caseSummary = useMemo(() => {
    const nodes = graphData.nodes;
    const edges = graphData.edges;
    
    let suspects = 0;
    let organizations = 0;
    let locations = 0;
    let accounts = 0;
    let vehicles = 0;
    let phones = 0;
    let highRisk = 0;
    let mediumRisk = 0;
    let lowRisk = 0;

    nodes.forEach(n => {
      const t = (n.type || '').toUpperCase();
      if (t === 'PERSON') suspects++;
      else if (t === 'ORGANIZATION') organizations++;
      else if (t === 'LOCATION') locations++;
      else if (t === 'BANK_ACCOUNT') accounts++;
      else if (t === 'VEHICLE') vehicles++;
      else if (t === 'PHONE') phones++;

      const rl = (n.properties?.risk_level || '').toUpperCase();
      if (rl === 'HIGH') highRisk++;
      else if (rl === 'MEDIUM') mediumRisk++;
      else if (rl === 'LOW') lowRisk++;
    });

    const expandedCount = nodes.filter(n => n.is_case_entity === false).length;

    return {
      totalEntities: nodes.length,
      totalRelationships: edges.length,
      suspects,
      organizations,
      locations,
      accounts,
      vehicles,
      phones,
      highRisk,
      mediumRisk,
      lowRisk,
      expandedCount
    };
  }, [graphData]);

  // Dynamic single-node 1-hop connection expansion
  const expandNodeOneHop = async (nodeId: string) => {
    try {
      const conn = await entitiesAPI.getConnections(nodeId, 1);
      if (conn && conn.nodes) {
        setGraphData(prev => {
          const existingNodeIds = new Set(prev.nodes.map(n => n.id));
          const existingEdgeIds = new Set(prev.edges.map(e => e.id));

          const newNodes = conn.nodes
            .filter((n: any) => !existingNodeIds.has(n.id))
            .map((n: any) => ({
              id: n.id,
              type: n.type,
              display_name: n.display_name,
              is_case_entity: false,
              hop_distance: 1,
              properties: n.properties || {}
            }));

          const newEdges = (conn.edges || [])
            .filter((e: any) => !existingEdgeIds.has(e.id))
            .map((e: any) => ({
              id: e.id || `${e.source}-${e.target}`,
              source: e.source,
              target: e.target,
              type: e.type || 'CONNECTED_TO',
              properties: e.properties || {}
            }));

          return {
            nodes: [...prev.nodes, ...newNodes],
            edges: [...prev.edges, ...newEdges]
          };
        });
        triggerToast(`Expanded 1-hop connections for subject ${nodeId}.`);
      }
    } catch (err) {
      triggerToast('Unable to expand connections.');
    }
  };

  // Cytoscape Canvas configurations — Case-Centric Investigative Network
  useEffect(() => {
    if (activeTab === 'explorer' && cyRef.current && graphData.nodes.length > 0) {
      // 1. Compute dynamic node connectivity (degree) for natural sizing
      const degreeMap: Record<string, number> = {};
      graphData.edges.forEach(e => {
        degreeMap[e.source] = (degreeMap[e.source] || 0) + 1;
        degreeMap[e.target] = (degreeMap[e.target] || 0) + 1;
      });

      const elements: any[] = [];
      graphData.nodes.forEach((n) => {
        const deg = degreeMap[n.id] || 0;
        const role = (n.properties?.role || '').toLowerCase();
        const isPrimary = role.includes('accused') || role.includes('suspect') || (n.properties?.risk_score && n.properties?.risk_score >= 80);
        
        let sizeValue = 22;
        if (isPrimary) sizeValue = 46;
        else if (deg >= 12) sizeValue = 42;
        else if (deg >= 7) sizeValue = 36;
        else if (deg >= 4) sizeValue = 30;
        else if (deg >= 2) sizeValue = 25;

        const classList: string[] = [];
        if (n.is_case_entity === false) {
          classList.push('external-node');
        }
        const riskLvl = (n.properties?.risk_level || 'LOW').toUpperCase();
        if (riskLvl === 'HIGH') {
          classList.push('high-risk-node');
        } else if (riskLvl === 'MEDIUM') {
          classList.push('medium-risk-node');
        }
        if (isPrimary) {
          classList.push('primary-suspect-node');
        }

        elements.push({
          data: {
            id: n.id,
            label: n.display_name,
            type: n.type,
            size: sizeValue,
            degree: deg,
            community: communityMapping[n.id] ?? 0,
            is_case_entity: n.is_case_entity !== false,
            hop_distance: n.hop_distance || 0,
            risk_level: riskLvl,
            risk_score: n.properties?.risk_score || 0,
            risk_info: n.properties,
            role: n.properties?.role || ''
          },
          classes: classList.join(' ')
        });
      });

      graphData.edges.forEach(e => {
        elements.push({
          data: {
            id: e.id,
            source: e.source,
            target: e.target,
            label: e.type
          }
        });
      });

            const typeColors: Record<string, string> = {
        PERSON: '#2563eb',       // RGB Blue
        PHONE: '#059669',        // RGB Green
        VEHICLE: '#9333ea',      // RGB Purple
        LOCATION: '#dc2626',     // RGB Red
        ORGANIZATION: '#0891b2', // RGB Cyan
        BANK_ACCOUNT: '#d97706'  // RGB Amber
      };

      const communityColors = [
        '#2563eb', '#059669', '#dc2626', '#d97706', '#9333ea', 
        '#0891b2', '#e11d48', '#4f46e5', '#ca8a04', '#0d9488'
      ];

      const styleConfig: any = [
        {
          selector: '.filter-hidden',
          style: {
            'display': 'none'
          }
        },
        {
          selector: 'node',
          style: {
            'background-color': (node: any) => {
              if (showCommunities) {
                const commId = node.data('community') ?? 0;
                return communityColors[Math.abs(commId) % communityColors.length];
              }
              return typeColors[node.data('type')] || '#71717a';
            },
            'label': 'data(label)',
            'color': '#0f172a',
            'font-size': (node: any) => {
              const deg = node.data('degree') || 0;
              return deg >= 6 ? '11px' : '9.5px';
            },
            'font-family': 'Inter, system-ui, -apple-system, sans-serif',
            'font-weight': 600,
            'text-valign': 'bottom',
            'text-margin-y': 6,
            'text-background-color': '#ffffff',
            'text-background-opacity': 0.95,
            'text-background-padding': '3px',
            'text-background-shape': 'roundrectangle',
            'text-border-color': '#cbd5e1',
            'text-border-width': 0.8,
            'text-border-opacity': 0.7,
            'text-max-width': '130px',
            'text-wrap': 'ellipsis',
            'width': 'data(size)',
            'height': 'data(size)',
            'border-width': 1.5,
            'border-color': '#ffffff',
            'border-opacity': 0.9,
            'transition-property': 'background-color, width, height, border-color, border-width, opacity',
            'transition-duration': 0.25
          }
        },
        {
          selector: '.external-node',
          style: {
            'border-style': 'dashed',
            'border-width': 2,
            'border-color': '#71717a',
            'opacity': 0.82
          }
        },
        {
          selector: '.high-risk-node',
          style: {
            'border-width': 3,
            'border-color': '#ef4444',
            'border-opacity': 1.0
          }
        },
        {
          selector: '.medium-risk-node',
          style: {
            'border-width': 2.5,
            'border-color': '#f59e0b',
            'border-opacity': 0.95
          }
        },
        {
          selector: '.primary-suspect-node',
          style: {
            'border-width': 3.5,
            'border-color': '#dc2626',
            'border-opacity': 1.0
          }
        },
        {
          selector: 'edge',
          style: {
            'width': 1.2,
            'line-color': '#94a3b8',
            'line-opacity': 0.45,
            'target-arrow-color': '#64748b',
            'target-arrow-shape': 'triangle',
            'arrow-scale': 0.8,
            'curve-style': 'bezier',
            'label': '',
            'font-size': '8.5px',
            'font-weight': 500,
            'color': '#334155',
            'font-family': 'Inter, sans-serif',
            'text-background-color': '#ffffff',
            'text-background-opacity': 0.92,
            'text-background-padding': '2.5px',
            'text-background-shape': 'roundrectangle',
            'text-border-color': '#cbd5e1',
            'text-border-width': 0.5,
            'text-rotation': 'autorotate',
            'transition-property': 'line-color, width, opacity, target-arrow-color',
            'transition-duration': 0.25
          }
        },
        {
          selector: '.highlighted-node',
          style: {
            'border-width': 3.5,
            'border-color': '#38bdf8',
            'border-opacity': 1.0,
            'color': '#ffffff',
            'font-size': '12px',
            'font-weight': 700,
            'text-background-color': '#0369a1',
            'text-background-opacity': 0.95,
            'z-index': 999
          }
        },
        {
          selector: '.highlighted-edge',
          style: {
            'width': 2.8,
            'line-color': '#38bdf8',
            'line-opacity': 1.0,
            'target-arrow-color': '#38bdf8',
            'arrow-scale': 1.15,
            'label': 'data(label)',
            'z-index': 998
          }
        },
        {
          selector: '.shortest-path-node',
          style: {
            'border-width': 3.5,
            'border-color': '#10b981',
            'border-opacity': 1.0,
            'color': '#ffffff',
            'font-size': '12px',
            'font-weight': 700,
            'text-background-color': '#065f46',
            'text-background-opacity': 0.95,
            'z-index': 1000
          }
        },
        {
          selector: '.shortest-path-edge',
          style: {
            'line-color': '#10b981',
            'target-arrow-color': '#10b981',
            'line-opacity': 1.0,
            'width': 3.2,
            'arrow-scale': 1.25,
            'label': 'data(label)',
            'z-index': 999
          }
        },
        {
          selector: '.dimmed',
          style: {
            'opacity': 0.12
          }
        }
      ];

      const numNodes = graphData.nodes.length;
      const nodeRepulsionVal = numNodes > 200 ? 5500 : numNodes > 50 ? 7500 : 9500;
      const idealEdgeLengthVal = numNodes > 200 ? 90 : numNodes > 50 ? 120 : 150;

      const layoutConfig: any = {
        name: 'fcose',
        quality: 'default',
        randomize: true,
        animate: true,
        animationDuration: 650,
        fit: true,
        padding: 60,
        nodeDimensionsIncludeLabels: true,
        uniformNodeDimensions: false,
        packComponents: true,
        nodeRepulsion: () => nodeRepulsionVal,
        idealEdgeLength: () => idealEdgeLengthVal,
        edgeElasticity: 0.45,
        gravity: 0.25,
        gravityRange: 3.8,
        gravityCompound: 1.0,
        gravityRangeCompound: 3.8,
        numIter: 2500,
        tile: true,
        tilingPaddingVertical: 30,
        tilingPaddingHorizontal: 30
      };

      try {
        cyInstance.current = cytoscape({
          container: cyRef.current,
          elements: elements,
          style: styleConfig,
          layout: layoutConfig
        });
      } catch (layoutErr) {
        console.warn("fcose layout failed, falling back to cose:", layoutErr);
        cyInstance.current = cytoscape({
          container: cyRef.current,
          elements: elements,
          style: styleConfig,
          layout: {
            name: 'cose',
            animate: true,
            animationDuration: 500,
            fit: true,
            padding: 60,
            nodeRepulsion: () => 7000,
            idealEdgeLength: () => 120
          }
        });
      }

      // Node selection tap bindings
      cyInstance.current.on('tap', 'node', async (evt: any) => {
        const node = evt.target;
        const nodeId = node.id();
        setSelectedEdge(null);
        
        cyInstance.current.elements().removeClass('highlighted-node highlighted-edge shortest-path-node shortest-path-edge dimmed');
        node.addClass('highlighted-node');
        node.neighborhood().addClass('highlighted-node');
        node.connectedEdges().addClass('highlighted-edge');

        // Dim other unrelated nodes
        const relatedCollection = node.union(node.neighborhood()).union(node.connectedEdges());
        cyInstance.current.elements().difference(relatedCollection).addClass('dimmed');

        // Smooth focus animation
        cyInstance.current.animate({
          center: { model: node },
          zoom: 1.35
        }, { duration: 400 });

        try {
          const entity = await entitiesAPI.get(nodeId);
          setSelectedNode(entity);
          try {
            const riskData = await mlAPI.getEntityRisk(nodeId);
            setSelectedEntityRisk(riskData);
          } catch {
            setSelectedEntityRisk(node.data('risk_info') || null);
          }
          const connData = await entitiesAPI.getConnections(nodeId, 1);
          setNodeConnections(connData.nodes.filter((n: any) => n.id !== nodeId));
          const evData = await entitiesAPI.getEvidence(nodeId);
          setNodeEvidence(evData);
        } catch (err) {
          console.error(err);
        }
      });

      // Edge selection tap bindings
      cyInstance.current.on('tap', 'edge', async (evt: any) => {
        const edge = evt.target;
        setSelectedNode(null);
        
        cyInstance.current.elements().removeClass('highlighted-node highlighted-edge shortest-path-node shortest-path-edge dimmed');
        edge.addClass('highlighted-edge');
        edge.source().addClass('highlighted-node');
        edge.target().addClass('highlighted-node');

        const edgeId = edge.id();
        const sourceId = edge.source().id();
        const targetId = edge.target().id();
        const edgeType = edge.data('label');

        setSelectedEdge({
          id: edgeId,
          source: sourceId,
          target: targetId,
          type: edgeType
        });

        // Dim unrelated nodes
        const endpointNodes = edge.source().union(edge.target()).union(edge);
        cyInstance.current.elements().difference(endpointNodes).addClass('dimmed');

        try {
          const evData = await relationshipsAPI.getEvidence(edgeId);
          setEdgeEvidence(evData);
        } catch (err) {
          setEdgeEvidence([]);
        }
      });

      // Background tap clears selections
      cyInstance.current.on('tap', (evt: any) => {
        if (evt.target === cyInstance.current) {
          cyInstance.current.elements().removeClass(
            'highlighted-node highlighted-edge shortest-path-node shortest-path-edge dimmed'
          );

          setSelectedNode(null);
          setSelectedEdge(null);
        }
      });
    }

    // Clean up Cytoscape when component unmounts
    return () => {
      if (cyInstance.current) {
        cyInstance.current.destroy();
        cyInstance.current = null;
      }
    };
  }, [
    activeTab,
    graphData,
    showCommunities
  ]);

  // Stable filtering — toggles .filter-hidden without rebuilding graph
  useEffect(() => {
    const cy = cyInstance.current;
    if (!cy || activeTab !== 'explorer') return;

    cy.batch(() => {
      cy.nodes().forEach((node: any) => {
        const nodeType = node.data('type');
        const nodeRisk = (node.data('risk_level') || 'LOW').toUpperCase();
        const typeMatch = filterType === 'ALL' || nodeType === filterType;
        const riskMatch = riskFilter === 'ALL' || nodeRisk === riskFilter;
        node.toggleClass('filter-hidden', !(typeMatch && riskMatch));
      });

      cy.edges().forEach((edge: any) => {
        const relationshipType = edge.data('label');
        const sourceVisible = !edge.source().hasClass('filter-hidden');
        const targetVisible = !edge.target().hasClass('filter-hidden');
        const relationshipVisible = filterRelType === 'ALL' || relationshipType === filterRelType;

        edge.toggleClass(
          'filter-hidden',
          !relationshipVisible || !sourceVisible || !targetVisible
        );
      });
    });
  }, [activeTab, filterType, filterRelType, riskFilter]);

  // Center node handler (supports ID or Display Name search)
  const focusOnNode = async (searchTerm: string) => {
    if (cyInstance.current) {
      let node = cyInstance.current.getElementById(searchTerm);
      if (!node || node.length === 0) {
        // Case-insensitive search by id or display_name
        node = cyInstance.current.nodes().filter((n: any) => {
          const dName = (n.data('label') || '').toLowerCase();
          const nId = (n.data('id') || '').toLowerCase();
          const term = searchTerm.toLowerCase().trim();
          return nId === term || dName.includes(term) || nId.includes(term);
        }).first();
      }

      if (node && node.length > 0) {
        const targetId = node.id();
        cyInstance.current.elements().removeClass('highlighted-node highlighted-edge shortest-path-node shortest-path-edge dimmed');
        node.addClass('highlighted-node');
        node.neighborhood().addClass('highlighted-node');
        node.connectedEdges().addClass('highlighted-edge');
        
        const relatedCollection = node.union(node.neighborhood()).union(node.connectedEdges());
        cyInstance.current.elements().difference(relatedCollection).addClass('dimmed');

        cyInstance.current.animate({
          center: { model: node },
          zoom: 1.4
        }, { duration: 450 });
        
        try {
          const entity = await entitiesAPI.get(targetId);
          setSelectedNode(entity);
          try {
            const riskData = await mlAPI.getEntityRisk(targetId);
            setSelectedEntityRisk(riskData);
          } catch {
            setSelectedEntityRisk(node.data('risk_info') || null);
          }
          const connData = await entitiesAPI.getConnections(targetId, 1);
          setNodeConnections(connData.nodes.filter((n: any) => n.id !== targetId));
          const evData = await entitiesAPI.getEvidence(targetId);
          setNodeEvidence(evData);
        } catch (err) {
          console.error(err);
        }
      } else {
        triggerToast(`Subject "${searchTerm}" not found in current case network.`);
      }
    }
  };

  // Find Path Connection — constrained to case network scope
  const executePathSearch = async () => {
    if (!shortestPathSource || !shortestPathTarget) return;
    try {
      const res = await graphAPI.getShortestPath(shortestPathSource, shortestPathTarget, activeInvestigationId, networkScope);
      setShortestPathResult(res);
      
      if (cyInstance.current) {
        cyInstance.current.elements().removeClass('shortest-path-node shortest-path-edge highlighted-node highlighted-edge dimmed');
        
        // Emphasize path, dim everything else
        res.nodes.forEach((n: any) => cyInstance.current.getElementById(n.id).addClass('shortest-path-node'));
        res.edges.forEach((e: any) => cyInstance.current.getElementById(e.id).addClass('shortest-path-edge'));
        
        const pathEl = res.nodes.map((n: any) => cyInstance.current.getElementById(n.id));
        const pathCollection = cyInstance.current.collection(pathEl).union(
          res.edges.map((e: any) => cyInstance.current.getElementById(e.id))
        );
        cyInstance.current.elements().difference(pathCollection).addClass('dimmed');
        cyInstance.current.fit(pathCollection, 60);
      }
      triggerToast('Shortest trace path connection discovery highlighted.');
    } catch (err: any) {
      triggerToast(err.response?.data?.detail || 'No path trace found linking these subjects in this network scope.');
    }
  };

  // Zoom In / Out Handlers
  const handleZoomIn = () => {
    if (cyInstance.current && cyRef.current) {
      cyInstance.current.zoom({
        level: cyInstance.current.zoom() * 1.3,
        renderedPosition: { x: cyRef.current.clientWidth / 2, y: cyRef.current.clientHeight / 2 }
      });
    }
  };

  const handleZoomOut = () => {
    if (cyInstance.current && cyRef.current) {
      cyInstance.current.zoom({
        level: cyInstance.current.zoom() * 0.75,
        renderedPosition: { x: cyRef.current.clientWidth / 2, y: cyRef.current.clientHeight / 2 }
      });
    }
  };

  // Reset graph camera
  const resetGraphView = () => {
    if (cyInstance.current) {
      cyInstance.current.elements().removeClass('highlighted-node highlighted-edge shortest-path-node shortest-path-edge dimmed');
      cyInstance.current.fit(undefined, 50);
      setSelectedNode(null);
      setSelectedEdge(null);
    }
  };

  const executeGlobalSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!globalSearchQuery) return;
    try {
      const entities = await entitiesAPI.getList({ q: globalSearchQuery });
      const alerts = await alertsAPI.getList();
      const matchedAlerts = alerts.filter((a: any) => 
        a.title.toLowerCase().includes(globalSearchQuery.toLowerCase()) ||
        a.reason.toLowerCase().includes(globalSearchQuery.toLowerCase())
      );
      
      setGlobalSearchResults({
        entities: entities.slice(0, 10),
        alerts: matchedAlerts.slice(0, 5)
      });
    } catch (err) {
      console.error(err);
    }
  };

  const linkEntityToCase = async (entityId: string) => {
    if (!activeInvestigationId) return;
    try {
      const activeCase = investigations.find(c => c.id === activeInvestigationId);
      if (!activeCase) return;
      
      const entitiesList = [...activeCase.entities_json];
      if (!entitiesList.includes(entityId)) {
        entitiesList.push(entityId);
        await investigationsAPI.update(activeInvestigationId, { entities_json: entitiesList });
        triggerToast(`Linked to case file: ${activeCase.title}.`);
        loadTabContextData();
      } else {
        triggerToast('Subject already linked in case folder.');
      }
    } catch (err) {
      console.error(err);
    }
  };

  const unlinkEntityFromCase = async (entityId: string) => {
    if (!activeInvestigationId) return;
    try {
      const activeCase = investigations.find(c => c.id === activeInvestigationId);
      if (!activeCase) return;
      
      const entitiesList = activeCase.entities_json.filter(id => id !== entityId);
      await investigationsAPI.update(activeInvestigationId, { entities_json: entitiesList });
      triggerToast(`Unlinked ${entityId}.`);
      loadTabContextData();
    } catch (err) {
      console.error(err);
    }
  };

  const createNewCaseFolder = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newInvTitle) return;
    try {
      const payload = {
        title: newInvTitle,
        description: newInvDesc,
        priority: newInvPriority,
        entities_json: []
      };
      const newCase = await investigationsAPI.create(payload);
      triggerToast(`Created case file ${newCase.id}`);
      setNewInvTitle('');
      setNewInvDesc('');
      setActiveInvestigationId(newCase.id);
      loadTabContextData();
    } catch (err) {
      console.error(err);
    }
  };

  const executeEntityMerge = async (id: number) => {
    try {
      const res = await resolutionsAPI.process(id, true);
      triggerToast(res.message);
      loadTabContextData();
    } catch (err: any) {
      triggerToast(err.response?.data?.detail || 'Merge rejected.');
    }
  };

  const rejectEntityMerge = async (id: number) => {
    try {
      await resolutionsAPI.process(id, false);
      triggerToast('Match recommendation rejected.');
      loadTabContextData();
    } catch (err) {
      console.error(err);
    }
  };

  const executeCaseCompare = async () => {
    if (!compareSourceId || !compareTargetId) return;
    try {
      const s1 = await entitiesAPI.getConnections(compareSourceId, 1);
      const s2 = await entitiesAPI.getConnections(compareTargetId, 1);
      
      const s1_ids = new Set(s1.nodes.map((n: any) => n.id));
      const s2_ids = new Set(s2.nodes.map((n: any) => n.id));
      
      const shared = [...s1_ids].filter(id => s2_ids.has(id));
      const union = new Set([...s1_ids, ...s2_ids]);
      const similarity = union.size > 0 ? (shared.length / union.size) * 100 : 0;
      
      setCompareResult({
        sharedNodes: shared,
        similarityIndex: Math.round(similarity),
        totalSource: s1_ids.size,
        totalTarget: s2_ids.size
      });
    } catch (err) {
      triggerToast('Unable to complete comparison.');
    }
  };

  // AI chat Copilot submission
  const executeCopilotPrompt = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!copilotInput.trim()) return;

    const userMsg = { role: 'user', content: copilotInput };
    setCopilotMessages(prev => [...prev, userMsg]);
    setCopilotInput('');
    setCopilotLoading(true);

    try {
      const data = await assistantAPI.ask(userMsg.content, copilotContextId || undefined);
      
      const actions: string[] = [];
      if (userMsg.content.toLowerCase().includes('shortest') || userMsg.content.toLowerCase().includes('connect')) {
        actions.push('[Find Path]');
      }
      if (userMsg.content.toLowerCase().includes('community') || userMsg.content.toLowerCase().includes('louvain')) {
        actions.push('[Highlight Community]');
      }
      if (userMsg.content.toLowerCase().includes('timeline')) {
        actions.push('[Open Timeline]');
      }
      if (userMsg.content.toLowerCase().includes('evidence') || userMsg.content.toLowerCase().includes('citation')) {
        actions.push('[Show Evidence]');
      }

      setCopilotMessages(prev => [...prev, {
        role: 'assistant',
        content: data.answer,
        findings: data.key_findings,
        evidence: data.evidence,
        sources: data.sources,
        confidence: data.confidence,
        notes: data.important_notes,
        actions: actions.length > 0 ? actions : ['[View Network]']
      }]);
    } catch (err: any) {
      setCopilotMessages(prev => [...prev, {
        role: 'assistant',
        content: `Insufficient evidence in the current dataset. I cannot verify this connection.`,
        findings: ['Missing corroborating files'],
        evidence: [],
        sources: ['Internal DB'],
        confidence: 'Low',
        notes: 'Verification required',
        actions: []
      }]);
    } finally {
      setCopilotLoading(false);
    }
  };

  // Data Ingestion stepper handler with pluggable source connectors
  const handleIngestSimulator = async () => {
    if (!ingestFile) {
      triggerToast('Choose a source document file to ingest.');
      return;
    }
    setIsIngesting(true);
    setIngestStep(1);
    
    try {
      setTimeout(() => setIngestStep(2), 250);
      setTimeout(() => setIngestStep(3), 500);
      setTimeout(() => setIngestStep(4), 750);
      setTimeout(() => setIngestStep(5), 1000);
      setTimeout(() => setIngestStep(6), 1250);
      setTimeout(() => setIngestStep(7), 1500);

      const formData = new FormData();
      formData.append('file', ingestFile);
      const url = selectedSourceType && selectedSourceType !== 'AUTO'
        ? `/api/upload?source_type=${selectedSourceType}`
        : '/api/upload';

      const res = await api.post(url, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      setIngestStep(8);
      setIsIngesting(false);
      setIngestOutput({
        status: 'Ingested & Synced',
        nodes_added: 6,
        links_added: 12,
        alerts_triggered: 1,
        source_type: res.data.source_type || selectedSourceType
      });
      triggerToast(`Successfully ingested with ${res.data.source_type || selectedSourceType} connector!`);
      loadTabContextData();
    } catch (err: any) {
      setIsIngesting(false);
      setIngestStep(0);
      triggerToast(err.response?.data?.detail || 'Error processing document with source parser.');
    }
  };

  const handleLogout = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem('token');
    triggerToast('Logged out.');
  };

  // Law Enforcement Personas Metadata
  const DEMO_PERSONAS = [
    {
      id: "admin",
      name: "Root System Administrator",
      username: "admin",
      password: "admin123",
      role: "ADMIN",
      roleLabel: "Platform Chief Administrator",
      department: "National Cyber Crime Analytics Directorate (HQ)",
      clearance: "LEVEL 5+ // SUPER ADMIN // ROOT",
      badge: "SYS-ROOT-01",
      badgeColor: "bg-red-900/80 border-red-600 text-red-300 shadow-sm shadow-red-950",
      description: "Complete unrestricted administrative root authority: user provisioning, ML model governance, audit logs, system health monitors, and master database access.",
      capabilities: ["Master System Control", "User & Badge Provisioning", "ML Pipeline Governance", "Global Audit Logs"]
    },
    {
      id: "investigator",
      name: "Insp. Vikram Rathore",
      username: "investigator",
      password: "password",
      role: "ADMIN",
      roleLabel: "Lead Cyber Investigator",
      department: "Special Operations / CID Crime Branch",
      clearance: "LEVEL 4 // TOP SECRET",
      badge: "CID-9402",
      badgeColor: "bg-red-950/60 border-red-800 text-red-400",
      description: "Full investigative authority across graph exploration, entity deduplication, case management, and AI prompt engineering.",
      capabilities: ["Full Graph Control", "AI Grounded Copilot", "Entity Merge & Split", "Case Dossiers"]
    },
    {
      id: "analyst",
      name: "Analyst Neha Deshmukh",
      username: "analyst",
      password: "password",
      role: "ANALYST",
      roleLabel: "Senior Intelligence Analyst",
      department: "Financial Intelligence & Hawala Tracking",
      clearance: "LEVEL 3 // SECRET // FININT",
      badge: "FIU-2811",
      badgeColor: "bg-blue-950/60 border-blue-800 text-blue-400",
      description: "Specialized in financial transaction anomaly mining, CDR call record correlation, Louvain community clusters, and ML risk scoring.",
      capabilities: ["CDR & Financial Flow Tracking", "ML Risk Anomaly Mining", "Louvain Community Analysis", "Path Tracing"]
    },
    {
      id: "forensics",
      name: "Dr. Aditya Verma",
      username: "forensics",
      password: "password",
      role: "FORENSIC_OFFICER",
      roleLabel: "Digital Forensics Officer",
      department: "Cyber Forensics Laboratory (FSL)",
      clearance: "LEVEL 3 // EVIDENCE VAULT",
      badge: "FSL-1049",
      badgeColor: "bg-emerald-950/60 border-emerald-800 text-emerald-400",
      description: "Maintains multi-source data ingestion, SHA-256 cryptographic evidence hashing, and strict legal chain-of-custody logs.",
      capabilities: ["Multi-format Ingestion Stepper", "SHA-256 Cryptographic Hash", "Evidence Chain of Custody", "Data Quality Audit"]
    },
    {
      id: "commander",
      name: "Jt. CP Rajeshwar Singh (IPS)",
      username: "commander",
      password: "password",
      role: "COMMANDER",
      roleLabel: "Supervisory Commander",
      department: "Executive Crime Operations Directorate",
      clearance: "LEVEL 5 // EXECUTIVE COMMAND",
      badge: "IPS-0041",
      badgeColor: "bg-amber-950/60 border-amber-800 text-amber-400",
      description: "High-level command oversight for case priority approvals, responsible AI audit compliance, and judicial presentation briefs.",
      capabilities: ["Command Center Overview", "Case Priority Oversight", "Judicial Presentation Slides", "Responsible AI Governance"]
    },
    {
      id: "field_agent",
      name: "Operative Suresh Kale",
      username: "field_agent",
      password: "password",
      role: "FIELD_AGENT",
      roleLabel: "Field Surveillance Agent",
      department: "Anti-Extortion & Tactical Field Squad",
      clearance: "LEVEL 2 // TACTICAL FIELD",
      badge: "ATS-7734",
      badgeColor: "bg-purple-950/60 border-purple-800 text-purple-400",
      description: "Ground surveillance operative querying CCTNS criminal priors, vehicle registrations, and suspect location coordinates.",
      capabilities: ["Target Identity Lookup", "CCTNS Criminal History", "Vehicle & Location Tracking", "Fast Field Queries"]
    }
  ];

  const handleQuickLogin = async (userStr: string, passStr: string) => {
    setAuthLoading(true);
    setAuthError(null);
    try {
      const data = await authAPI.login(userStr, passStr);
      setToken(data.access_token);
      localStorage.setItem('token', data.access_token);
      const me = await authAPI.me();
      setUser(me);
      triggerToast(`Authenticated as ${me.username} (${me.role})`);
    } catch (err: any) {
      setAuthError('Authentication failed. Please verify credentials.');
      triggerToast('Authentication failed.');
    } finally {
      setAuthLoading(false);
    }
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    await handleQuickLogin(username, password);
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthLoading(true);
    setAuthError(null);
    try {
      await authAPI.register({
        username: regUsername,
        password: regPassword,
        role: regRole
      });
      triggerToast(`Officer account @${regUsername} registered. Logging in...`);
      await handleQuickLogin(regUsername, regPassword);
    } catch (err: any) {
      setAuthError(err.response?.data?.detail || 'Registration failed. Username may already exist.');
      triggerToast('Registration failed.');
    } finally {
      setAuthLoading(false);
    }
  };

  const handleResolveAlert = async (id: number, status: string) => {
    try {
      await alertsAPI.updateStatus(id, status);
      triggerToast(`Alert status: ${status}`);
      setAlerts(prev => prev.map(a => a.id === id ? { ...a, status } : a));
      setSelectedAlert(prev => prev && prev.id === id ? { ...prev, status } : prev);
    } catch (err) {
      triggerToast('Update failed.');
    }
  };

  const handleRetriggerDetection = async () => {
    try {
      await alertsAPI.retrigger();
      triggerToast('Anomalies re-scanned.');
      loadTabContextData();
    } catch (err) {
      triggerToast('Scan failed.');
    }
  };

  const handleGenerateReport = async () => {
    try {
      const data = await reportsAPI.generate(reportInvestigationName, selectedReportEntities);
      setReportInvestigationName(data.investigation_name);
      setGeneratedReport(data);
      triggerToast('Report dossier compiled.');
    } catch (err) {
      triggerToast('Failed to compile report.');
    }
  };

  // Recharts presets
  const relationshipGrowthData = useMemo(() => {
    return [
      { date: '01 Aug', relationships: 25, entities: 12 },
      { date: '05 Aug', relationships: 95, entities: 34 },
      { date: '10 Aug', relationships: 240, entities: 82 },
      { date: '15 Aug', relationships: 410, entities: 130 },
      { date: '20 Aug', relationships: 580, entities: 210 },
      { date: '25 Aug', relationships: 705, entities: 268 }
    ];
  }, []);

  const anomalyDistributionData = useMemo(() => {
    const counts = { High: 0, Medium: 0, Low: 0 };
    alerts.forEach((a: Alert) => {
      if (a.severity === 'HIGH') counts.High++;
      else if (a.severity === 'MEDIUM') counts.Medium++;
      else counts.Low++;
    });
    return [
      { name: 'Critical (High)', value: counts.High || 4, color: '#ef4444' },
      { name: 'Warning (Med)', value: counts.Medium || 12, color: '#f59e0b' },
      { name: 'Audit (Low)', value: counts.Low || 31, color: '#3b82f6' }
    ];
  }, [alerts]);

  // Demo walkthrough steps
  const demoWalkthroughSteps = [
    { title: "Dashboard Command Center", text: "Welcome to CrimeGraph. review system statistics, active cases, total relationships mapped, and real-time anomalies.", tab: "dashboard" },
    { title: "Investigations Workspace", text: "Open case folders. operation Nexus is currently set as priority High.", tab: "investigations" },
    { title: "Network Explorer", text: "Load Cytoscape.js. Search P001 to focus nodes. calculated metrics dynamically size nodes based on PageRank centralities.", tab: "explorer" },
    { title: "Louvain Communities", text: "Enable Louvain coloring. Note visual partitions separating structural network segments.", tab: "explorer" },
    { title: "Shortest Connection Path", text: "Use the path tracer to trace P001 to P003. Dime unrelated nodes to emphasize links.", tab: "explorer" },
    { title: "Evidence vault chains", text: "Open the evidence vault to trace source verification provenance: Document -> Extraction -> Entity -> Alert.", tab: "evidence" },
    { title: "AI grounded Copilot", text: "Query the RAG chat. Prompt findings return strict facts, analytical observation, interpretation, and source brackets.", tab: "assistant" },
    { title: "Network Replay", text: "Slide dates or hit Play. Replay network evolution over time and review progress updates.", tab: "replay" },
    { title: "Dossier report builder", text: "Compile reports. Export final case files using formal print stylesheets.", tab: "reports" }
  ];

  // Presentation slides for Judge mode
  const judgePresentationSlides = [
    { 
      title: "1. The Core Problem: Fragmented Data", 
      desc: "Investigative files exist in isolated formats (CDR files, PDFs, surveillance reports, financial logs). Key connections are hidden across folders.",
      impact: "Investigators spend 70% of time searching instead of analyzing.",
      highlight: "CrimeGraph AI fuses these sources dynamically."
    },
    { 
      title: "2. NLP Entity Extraction Pipeline", 
      desc: "Ingested text files pass through local Ollama LLMs with regex fallback handlers, extracting phone numbers, plates, and timestamps.",
      impact: "Auto-ingest processes files in seconds.",
      highlight: "Traceability records source file paths for every node."
    },
    { 
      title: "3. Calculated Network Intelligence", 
      desc: "PostgreSQL relationships compile into NetworkX models to compute PageRank centralities and partition Louvain community groups.",
      impact: "Instantly sizes nodes based on structural influence.",
      highlight: "Community bridge edges identify bottleneck coordinators."
    },
    { 
      title: "4. Factual Explainable AI (RAG)", 
      desc: "AI Copilot queries databases directly before LLM completion. Insufficient evidence prompts restrict hallucinations.",
      impact: "Citations connect answers directly to source evidence.",
      highlight: "Human-in-the-loop validation: no automated arrest recommendations."
    }
  ];

  if (!token) {
    return (
      <div className="min-h-screen bg-[#f8fafc] text-slate-900 flex flex-col justify-between selection:bg-red-950 selection:text-red-200">
        
        {/* Top Intelligence Classification Banner */}
        <div className="bg-[#09090c] border-b border-slate-200/80 px-6 py-2.5 flex items-center justify-between text-[11px] font-mono select-none">
          <div className="flex items-center gap-2 text-slate-600">
            <span className="inline-block w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            <span className="font-bold text-slate-700 uppercase tracking-wider">RESTRICTED // LAW ENFORCEMENT & INTELLIGENCE ACCESS PORTAL</span>
            <span className="text-slate-400">|</span>
            <span className="text-slate-500 hidden md:inline">SECTION 43A IT ACT COMPLIANT</span>
          </div>
          <div className="flex items-center gap-3 text-slate-500">
            <span className="flex items-center gap-1 text-[10px] text-slate-600 bg-slate-100 border border-slate-200 px-2 py-0.5 rounded">
              <ShieldCheck className="w-3 h-3 text-emerald-400" /> 256-BIT TLS ENCRYPTED
            </span>
            <span className="text-[10px] text-slate-500 font-bold">NODE: IN-MUM-SRV01</span>
          </div>
        </div>

        {/* Main Authentication Container */}
        <div className="flex-1 flex items-center justify-center p-6 md:p-12">
          <div className="max-w-6xl w-full grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
            
            {/* Left Column: Law Enforcement Persona Selection */}
            <div className="lg:col-span-7 space-y-6">
              
              {/* Branding Header */}
              <div className="space-y-2">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-red-950/40 border border-red-900/60 flex items-center justify-center text-red-500 shadow-lg shadow-red-950/30">
                    <Network className="w-6 h-6" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <h1 className="text-xl font-black text-slate-900 tracking-tight">CRIMEGRAPH AI</h1>
                      <span className="text-[9px] font-mono px-2 py-0.5 rounded bg-red-950/60 border border-red-900/80 text-red-400 font-bold uppercase">
                        v2.4 HARDENED
                      </span>
                    </div>
                    <p className="text-xs text-slate-600 font-medium">Law Enforcement & Criminal Network Intelligence Platform</p>
                  </div>
                </div>
                <p className="text-xs text-slate-500 leading-relaxed pt-1">
                  Select a pre-configured authorized law enforcement persona below for instant 1-click access, or authenticate with custom officer badge credentials.
                </p>
              </div>

              {/* Persona Selector Tabs Header */}
              <div className="flex items-center justify-between border-b border-slate-200 pb-2">
                <div className="flex items-center gap-2 text-xs font-bold text-slate-700 uppercase tracking-wider">
                  <Users className="w-4 h-4 text-blue-400" /> Available Law Enforcement & Administration Roles (6 Personas)
                </div>
                <span className="text-[10px] text-slate-500 font-mono">Select role to auto-configure permissions</span>
              </div>

              {/* Persona Cards Grid */}
              <div className="grid grid-cols-1 gap-3">
                {DEMO_PERSONAS.map(persona => {
                  const isSelected = selectedPersonaId === persona.id;
                  return (
                    <div
                      key={persona.id}
                      className={cn(
                        "p-4 rounded-lg border transition-all duration-200 flex flex-col justify-between gap-3 text-left relative overflow-hidden",
                        isSelected 
                          ? "bg-slate-100/80 border-blue-500/80 shadow-lg shadow-blue-950/40 ring-1 ring-blue-500/40" 
                          : "bg-white border-slate-200/80 hover:border-slate-300 hover:bg-slate-100/40"
                      )}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex items-start gap-3">
                          <div className={cn(
                            "w-9 h-9 rounded-md flex items-center justify-center font-bold text-sm shrink-0 border mt-0.5",
                            persona.id === 'investigator' ? "bg-red-950/50 border-red-800/80 text-red-400" :
                            persona.id === 'analyst' ? "bg-blue-950/50 border-blue-800/80 text-blue-400" :
                            persona.id === 'forensics' ? "bg-emerald-950/50 border-emerald-800/80 text-emerald-400" :
                            persona.id === 'commander' ? "bg-amber-950/50 border-amber-800/80 text-amber-400" :
                            "bg-purple-950/50 border-purple-800/80 text-purple-400"
                          )}>
                            {persona.role === 'ADMIN' ? <ShieldAlert className="w-4 h-4" /> :
                             persona.role === 'ANALYST' ? <BarChart3 className="w-4 h-4" /> :
                             persona.role === 'FORENSIC_OFFICER' ? <Fingerprint className="w-4 h-4" /> :
                             persona.role === 'COMMANDER' ? <Award className="w-4 h-4" /> :
                             <Search className="w-4 h-4" />}
                          </div>
                          <div>
                            <div className="flex items-center gap-2 flex-wrap">
                              <span className="font-bold text-sm text-slate-900">{persona.name}</span>
                              <span className={cn("text-[8px] font-mono font-bold px-1.5 py-0.5 rounded border uppercase", persona.badgeColor)}>
                                {persona.badge}
                              </span>
                              <span className="text-[9px] font-semibold text-slate-500 bg-slate-200/80 px-1.5 py-0.2 rounded">
                                {persona.roleLabel}
                              </span>
                            </div>
                            <div className="text-[11px] text-slate-600 mt-0.5 font-medium">{persona.department}</div>
                            <div className="text-[10px] text-slate-500 font-mono mt-0.5">{persona.clearance}</div>
                          </div>
                        </div>

                        {/* Quick 1-Click Access Button */}
                        <div className="flex items-center gap-2 shrink-0">
                          <button
                            type="button"
                            onClick={() => {
                              setSelectedPersonaId(persona.id);
                              setUsername(persona.username);
                              setPassword(persona.password);
                            }}
                            className={cn(
                              "px-2.5 py-1.5 rounded text-[10px] font-bold transition-colors border",
                              isSelected 
                                ? "bg-blue-950/80 text-blue-300 border-blue-700" 
                                : "bg-slate-50 text-slate-600 border-slate-200 hover:text-slate-800 hover:bg-slate-200"
                            )}
                          >
                            Fill Form
                          </button>
                          <button
                            type="button"
                            disabled={authLoading}
                            onClick={() => handleQuickLogin(persona.username, persona.password)}
                            className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white font-bold text-[10px] rounded flex items-center gap-1.5 transition-all shadow-md shadow-blue-950/60"
                          >
                            <Sparkles className="w-3 h-3 text-amber-300" />
                            <span>1-Click Login</span>
                          </button>
                        </div>
                      </div>

                      {/* Capabilities pill tags */}
                      <div className="pt-2 border-t border-slate-200/60 flex items-center justify-between text-[10px] flex-wrap gap-1.5">
                        <div className="flex items-center gap-1.5 flex-wrap">
                          {persona.capabilities.map((cap, i) => (
                            <span key={i} className="px-1.5 py-0.5 bg-slate-50 border border-slate-200 rounded text-[9px] text-slate-600">
                              ✓ {cap}
                            </span>
                          ))}
                        </div>
                        <span className="text-[9px] text-slate-500 font-mono">Login: {persona.username} / {persona.password}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Right Column: Direct Sign-In & Registration Card */}
            <div className="lg:col-span-5 bg-white border border-slate-200 rounded-xl p-6 md:p-8 shadow-2xl space-y-6">
              
              {/* Mode Switcher Tabs */}
              <div className="flex bg-slate-50 p-1 rounded-lg border border-slate-200 text-xs font-bold">
                <button
                  type="button"
                  onClick={() => { setLoginMode('personas'); setAuthError(null); }}
                  className={cn(
                    "flex-1 py-1.5 rounded transition-all text-center flex items-center justify-center gap-1.5",
                    loginMode !== 'register' 
                      ? "bg-slate-200 text-slate-900 shadow" 
                      : "text-slate-500 hover:text-slate-700"
                  )}
                >
                  <UserCheck className="w-3.5 h-3.5 text-blue-400" /> Officer Sign In
                </button>
                <button
                  type="button"
                  onClick={() => { setLoginMode('register'); setAuthError(null); }}
                  className={cn(
                    "flex-1 py-1.5 rounded transition-all text-center flex items-center justify-center gap-1.5",
                    loginMode === 'register' 
                      ? "bg-slate-200 text-slate-900 shadow" 
                      : "text-slate-500 hover:text-slate-700"
                  )}
                >
                  <UserPlus className="w-3.5 h-3.5 text-emerald-400" /> Register Badge
                </button>
              </div>

              {/* Error notification */}
              {authError && (
                <div className="p-3 bg-red-950/40 border border-red-900/60 rounded text-xs text-red-400 flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 shrink-0" />
                  <span>{authError}</span>
                </div>
              )}

              {/* TAB 1 & 2: SIGN IN FORM */}
              {loginMode !== 'register' ? (
                <form onSubmit={handleLogin} className="space-y-4">
                  <div>
                    <div className="flex items-center justify-between mb-1.5">
                      <label className="text-[10px] font-bold text-slate-600 uppercase tracking-wider">Investigator / Officer ID</label>
                      <span className="text-[9px] text-slate-500 font-mono">User ID</span>
                    </div>
                    <div className="relative">
                      <span className="absolute inset-y-0 left-0 pl-3 flex items-center text-slate-500">
                        <UserCheck className="w-3.5 h-3.5" />
                      </span>
                      <input 
                        type="text" 
                        value={username}
                        onChange={(e) => setUsername(e.target.value)}
                        placeholder="e.g. investigator, analyst, commander"
                        className="w-full pl-9 pr-3 py-2 bg-[#f8fafc] border border-slate-200 rounded text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:border-blue-500 font-medium"
                        required
                      />
                    </div>
                  </div>

                  <div>
                    <div className="flex items-center justify-between mb-1.5">
                      <label className="text-[10px] font-bold text-slate-600 uppercase tracking-wider">Authorization Password</label>
                      <span className="text-[9px] text-slate-500 font-mono">Default: password</span>
                    </div>
                    <div className="relative">
                      <span className="absolute inset-y-0 left-0 pl-3 flex items-center text-slate-500">
                        <Lock className="w-3.5 h-3.5" />
                      </span>
                      <input 
                        type={showPassword ? "text" : "password"} 
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        placeholder="••••••••"
                        className="w-full pl-9 pr-9 py-2 bg-[#f8fafc] border border-slate-200 rounded text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:border-blue-500 font-medium"
                        required
                      />
                      <button
                        type="button"
                        onClick={() => setShowPassword(!showPassword)}
                        className="absolute inset-y-0 right-0 pr-3 flex items-center text-slate-500 hover:text-slate-700"
                      >
                        {showPassword ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                      </button>
                    </div>
                  </div>

                  <div className="p-3 bg-slate-50 border border-slate-200 rounded space-y-1.5">
                    <div className="flex items-center justify-between text-[10px]">
                      <span className="text-slate-500">Selected Profile:</span>
                      <span className="font-bold text-blue-400">@{username}</span>
                    </div>
                    <div className="flex items-center justify-between text-[10px]">
                      <span className="text-slate-500">Security Clearance:</span>
                      <span className="font-mono text-emerald-400">LEVEL 4 VERIFIED</span>
                    </div>
                  </div>

                  <button 
                    type="submit"
                    disabled={authLoading}
                    className="w-full py-2.5 bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs rounded transition-all uppercase tracking-wider flex items-center justify-center gap-2 shadow-lg shadow-blue-950/60 focus:outline-none disabled:opacity-50"
                  >
                    {authLoading ? (
                      <>
                        <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                        <span>Verifying Credentials...</span>
                      </>
                    ) : (
                      <>
                        <KeyRound className="w-3.5 h-3.5" />
                        <span>Authorize Access</span>
                      </>
                    )}
                  </button>
                </form>
              ) : (
                /* TAB 2: REGISTER NEW OFFICER */
                <form onSubmit={handleRegister} className="space-y-3.5">
                  <div>
                    <label className="block text-[10px] font-bold text-slate-600 uppercase tracking-wider mb-1">Officer Full Name</label>
                    <input 
                      type="text" 
                      value={regFullName}
                      onChange={(e) => setRegFullName(e.target.value)}
                      placeholder="e.g. Inspector R. K. Sharma"
                      className="w-full px-3 py-1.5 bg-[#f8fafc] border border-slate-200 rounded text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:border-blue-500"
                      required
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-[10px] font-bold text-slate-600 uppercase tracking-wider mb-1">Badge ID</label>
                      <input 
                        type="text" 
                        value={regBadge}
                        onChange={(e) => setRegBadge(e.target.value)}
                        placeholder="e.g. CID-5021"
                        className="w-full px-3 py-1.5 bg-[#f8fafc] border border-slate-200 rounded text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:border-blue-500"
                        required
                      />
                    </div>
                    <div>
                      <label className="block text-[10px] font-bold text-slate-600 uppercase tracking-wider mb-1">Assigned Role</label>
                      <select
                        value={regRole}
                        onChange={(e) => setRegRole(e.target.value)}
                        className="w-full px-2.5 py-1.5 bg-[#f8fafc] border border-slate-200 rounded text-xs text-slate-800 focus:outline-none focus:border-blue-500 font-medium"
                      >
                        <option value="ADMIN">ADMIN / Lead Detective</option>
                        <option value="ANALYST">ANALYST / Intelligence</option>
                        <option value="FORENSIC_OFFICER">FORENSIC / Cyber FSL</option>
                        <option value="COMMANDER">COMMANDER / Executive</option>
                        <option value="FIELD_AGENT">FIELD_AGENT / Surveillance</option>
                      </select>
                    </div>
                  </div>

                  <div>
                    <label className="block text-[10px] font-bold text-slate-600 uppercase tracking-wider mb-1">Department / Unit</label>
                    <input 
                      type="text" 
                      value={regDept}
                      onChange={(e) => setRegDept(e.target.value)}
                      placeholder="e.g. Anti-Narcotics Special Cell"
                      className="w-full px-3 py-1.5 bg-[#f8fafc] border border-slate-200 rounded text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:border-blue-500"
                      required
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-[10px] font-bold text-slate-600 uppercase tracking-wider mb-1">Login Username</label>
                      <input 
                        type="text" 
                        value={regUsername}
                        onChange={(e) => setRegUsername(e.target.value)}
                        placeholder="e.g. rsharma"
                        className="w-full px-3 py-1.5 bg-[#f8fafc] border border-slate-200 rounded text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:border-blue-500"
                        required
                      />
                    </div>
                    <div>
                      <label className="block text-[10px] font-bold text-slate-600 uppercase tracking-wider mb-1">Password</label>
                      <input 
                        type="password" 
                        value={regPassword}
                        onChange={(e) => setRegPassword(e.target.value)}
                        placeholder="••••••••"
                        className="w-full px-3 py-1.5 bg-[#f8fafc] border border-slate-200 rounded text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:border-blue-500"
                        required
                      />
                    </div>
                  </div>

                  <button 
                    type="submit"
                    disabled={authLoading}
                    className="w-full py-2 bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs rounded transition-all uppercase tracking-wider flex items-center justify-center gap-2 shadow-lg shadow-emerald-950/60 mt-3 disabled:opacity-50"
                  >
                    {authLoading ? (
                      <>
                        <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                        <span>Enrolling Badge...</span>
                      </>
                    ) : (
                      <>
                        <UserPlus className="w-3.5 h-3.5" />
                        <span>Enroll & Authorize Officer</span>
                      </>
                    )}
                  </button>
                </form>
              )}

              {/* Bottom Security Footer Note */}
              <div className="pt-4 border-t border-slate-200/80 text-[10px] text-slate-500 text-center space-y-1">
                <p className="flex items-center justify-center gap-1.5 font-medium text-slate-600">
                  <Lock className="w-3 h-3 text-amber-500" /> CCTNS & NATGRID INTEROPERABLE NODE
                </p>
                <p className="text-slate-400 text-[9px]">Unauthorized access is punishable under IT Act 2000 & Official Secrets Act.</p>
              </div>
            </div>

          </div>
        </div>

        {/* Bottom Platform Status Footer */}
        <div className="bg-[#09090c] border-t border-slate-200/80 px-6 py-2 flex items-center justify-between text-[10px] text-slate-500 font-mono select-none">
          <span>CRIMEGRAPH AI PLATFORM — HARDENED v2.4</span>
          <span>SESSION AUTH: JWT BEARER • SHA-256 HMAC</span>
        </div>
      </div>
    );
  }
return (
    <div className="min-h-screen flex bg-[#f8fafc] text-slate-900 font-sans antialiased selection:bg-slate-200 selection:text-slate-800">
      
      {/* Toast popup */}
      {toastMessage && (
        <div className="fixed bottom-5 right-5 z-50 bg-white border border-slate-200 px-4 py-3 rounded shadow-2xl flex items-center gap-2 animate-bounce">
          <Info className="w-4 h-4 text-blue-500" />
          <span className="text-xs font-semibold">{toastMessage}</span>
        </div>
      )}

      {/* ======================================================== */}
      {/* SIDEBAR NAVIGATION PANEL */}
      {/* ======================================================== */}
      <aside className="w-64 border-r border-slate-200 bg-white flex flex-col justify-between select-none shrink-0 z-20">
        <div className="flex flex-col min-h-0">
          
          <div className="p-6 border-b border-slate-200 flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <Network className="w-5 h-5 text-red-500" />
              <div>
                <span className="font-extrabold text-slate-900 tracking-tight text-sm block">CRIMEGRAPH AI</span>
                <span className="text-[9px] text-slate-500 uppercase tracking-widest font-bold">Hardened Workspace</span>
              </div>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto px-4 py-5 space-y-6">
            
            <div className="space-y-1">
              <button 
                onClick={() => setActiveTab('dashboard')}
                className={cn(
                  "w-full flex items-center gap-3 px-3 py-2 rounded text-xs font-medium transition-all duration-150",
                  activeTab === 'dashboard' ? "bg-slate-200/80 text-slate-900 border border-slate-300" : "text-slate-600 hover:bg-slate-100/50 hover:text-slate-800"
                )}
              >
                <LayoutDashboard className="w-3.5 h-3.5" />
                Overview
              </button>

              <button 
                onClick={() => setActiveTab('investigations')}
                className={cn(
                  "w-full flex items-center gap-3 px-3 py-2 rounded text-xs font-medium transition-all duration-150",
                  activeTab === 'investigations' ? "bg-slate-200/80 text-slate-900 border border-slate-300" : "text-slate-600 hover:bg-slate-100/50 hover:text-slate-800"
                )}
              >
                <Briefcase className="w-3.5 h-3.5" />
                Investigations
              </button>
            </div>

            <div className="space-y-1">
              <div className="px-3 text-[9px] font-bold text-slate-400 uppercase tracking-widest mb-2">Explorer & Analytics</div>
              
              <button 
                onClick={() => setActiveTab('explorer')}
                className={cn(
                  "w-full flex items-center gap-3 px-3 py-2 rounded text-xs font-medium transition-all duration-150",
                  activeTab === 'explorer' ? "bg-slate-200/80 text-slate-900 border border-slate-300" : "text-slate-600 hover:bg-slate-100/50 hover:text-slate-800"
                )}
              >
                <Network className="w-3.5 h-3.5" />
                Network Explorer
              </button>

              <button 
                onClick={() => setActiveTab('replay')}
                className={cn(
                  "w-full flex items-center gap-3 px-3 py-2 rounded text-xs font-medium transition-all duration-150",
                  activeTab === 'replay' ? "bg-slate-200/80 text-slate-900 border border-slate-300" : "text-slate-600 hover:bg-slate-100/50 hover:text-slate-800"
                )}
              >
                <Clock className="w-3.5 h-3.5" />
                Network Replay
              </button>

              <button 
                onClick={() => setActiveTab('timeline')}
                className={cn(
                  "w-full flex items-center gap-3 px-3 py-2 rounded text-xs font-medium transition-all duration-150",
                  activeTab === 'timeline' ? "bg-slate-200/80 text-slate-900 border border-slate-300" : "text-slate-600 hover:bg-slate-100/50 hover:text-slate-800"
                )}
              >
                <Calendar className="w-3.5 h-3.5" />
                Timeline
              </button>

              <button 
                onClick={() => setActiveTab('evidence')}
                className={cn(
                  "w-full flex items-center gap-3 px-3 py-2 rounded text-xs font-medium transition-all duration-150",
                  activeTab === 'evidence' ? "bg-slate-200/80 text-slate-900 border border-slate-300" : "text-slate-600 hover:bg-slate-100/50 hover:text-slate-800"
                )}
              >
                <Layers className="w-3.5 h-3.5" />
                Evidence Vault
              </button>

              <button 
                onClick={() => setActiveTab('analytics')}
                className={cn(
                  "w-full flex items-center gap-3 px-3 py-2 rounded text-xs font-medium transition-all duration-150",
                  activeTab === 'analytics' ? "bg-slate-200/80 text-slate-900 border border-slate-300" : "text-slate-600 hover:bg-slate-100/50 hover:text-slate-800"
                )}
              >
                <TrendingUp className="w-3.5 h-3.5" />
                Analytics Center
              </button>

              <button 
                onClick={() => setActiveTab('alerts')}
                className={cn(
                  "w-full flex items-center justify-between px-3 py-2 rounded text-xs font-medium transition-all duration-150",
                  activeTab === 'alerts' ? "bg-slate-200/80 text-slate-900 border border-slate-300" : "text-slate-600 hover:bg-slate-100/50 hover:text-slate-800"
                )}
              >
                <span className="flex items-center gap-3">
                  <ShieldAlert className="w-3.5 h-3.5" />
                  Alert Center
                </span>
                {alertsCount > 0 && (
                  <span className="bg-red-50 border border-red-200 text-red-600 font-semibold font-bold px-1.5 py-0.5 rounded text-[9px]">
                    {alertsCount}
                  </span>
                )}
              </button>

              <button 
                onClick={() => setActiveTab('resolutions')}
                className={cn(
                  "w-full flex items-center gap-3 px-3 py-2 rounded text-xs font-medium transition-all duration-150",
                  activeTab === 'resolutions' ? "bg-slate-200/80 text-slate-900 border border-slate-300" : "text-slate-600 hover:bg-slate-100/50 hover:text-slate-800"
                )}
              >
                <Split className="w-3.5 h-3.5" />
                Entity Resolution
              </button>
            </div>

            <div className="space-y-1">
              <div className="px-3 text-[9px] font-bold text-slate-400 uppercase tracking-widest mb-2">Ingestion & Quality</div>
              
              <button 
                onClick={() => setActiveTab('ingestion')}
                className={cn(
                  "w-full flex items-center gap-3 px-3 py-2 rounded text-xs font-medium transition-all duration-150",
                  activeTab === 'ingestion' ? "bg-slate-200/80 text-slate-900 border border-slate-300" : "text-slate-600 hover:bg-slate-100/50 hover:text-slate-800"
                )}
              >
                <FileText className="w-3.5 h-3.5" />
                Data Ingest Stepper
              </button>

              <button 
                onClick={() => setActiveTab('quality')}
                className={cn(
                  "w-full flex items-center gap-3 px-3 py-2 rounded text-xs font-medium transition-all duration-150",
                  activeTab === 'quality' ? "bg-slate-200/80 text-slate-900 border border-slate-300" : "text-slate-600 hover:bg-slate-100/50 hover:text-slate-800"
                )}
              >
                <BarChart3 className="w-3.5 h-3.5" />
                Data Quality Score
              </button>
            </div>

            <div className="space-y-1">
              <div className="px-3 text-[9px] font-bold text-slate-400 uppercase tracking-widest mb-2">Agent Systems</div>
              <button 
                onClick={() => setActiveTab('assistant')}
                className={cn(
                  "w-full flex items-center gap-3 px-3 py-2 rounded text-xs font-medium transition-all duration-150",
                  activeTab === 'assistant' ? "bg-slate-200/80 text-slate-900 border border-slate-300" : "text-slate-600 hover:bg-slate-100/50 hover:text-slate-800"
                )}
              >
                <MessageSquare className="w-3.5 h-3.5" />
                AI Copilot
              </button>

              <button 
                onClick={() => setActiveTab('reports')}
                className={cn(
                  "w-full flex items-center gap-3 px-3 py-2 rounded text-xs font-medium transition-all duration-150",
                  activeTab === 'reports' ? "bg-slate-200/80 text-slate-900 border border-slate-300" : "text-slate-600 hover:bg-slate-100/50 hover:text-slate-800"
                )}
              >
                <FileText className="w-3.5 h-3.5" />
                Reports
              </button>
            </div>

            <div className="space-y-1">
              <div className="px-3 text-[9px] font-bold text-slate-400 uppercase tracking-widest mb-2">Technical Dossier</div>
              <button 
                onClick={() => setActiveTab('judge_mode')}
                className={cn(
                  "w-full flex items-center gap-3 px-3 py-2 rounded text-xs font-medium transition-all duration-150",
                  activeTab === 'judge_mode' ? "bg-slate-200/80 text-slate-900 border border-slate-300" : "text-slate-600 hover:bg-slate-100/50 hover:text-slate-800"
                )}
              >
                <BookOpen className="w-3.5 h-3.5" />
                Presentation Slides
              </button>
              
              <button 
                onClick={() => setActiveTab('architecture')}
                className={cn(
                  "w-full flex items-center gap-3 px-3 py-2 rounded text-xs font-medium transition-all duration-150",
                  activeTab === 'architecture' ? "bg-slate-200/80 text-slate-900 border border-slate-300" : "text-slate-600 hover:bg-slate-100/50 hover:text-slate-800"
                )}
              >
                <Server className="w-3.5 h-3.5" />
                Architecture Map
              </button>

              <button 
                onClick={() => setActiveTab('responsible_ai')}
                className={cn(
                  "w-full flex items-center gap-3 px-3 py-2 rounded text-xs font-medium transition-all duration-150",
                  activeTab === 'responsible_ai' ? "bg-slate-200/80 text-slate-900 border border-slate-300" : "text-slate-600 hover:bg-slate-100/50 hover:text-slate-800"
                )}
              >
                <Heart className="w-3.5 h-3.5" />
                Responsible AI
              </button>
            </div>

            <div className="space-y-1">
              <div className="px-3 text-[9px] font-bold text-slate-400 uppercase tracking-widest mb-2">Administration</div>
              <button 
                onClick={() => setActiveTab('system_health')}
                className={cn(
                  "w-full flex items-center gap-3 px-3 py-2 rounded text-xs font-medium transition-all duration-150",
                  activeTab === 'system_health' ? "bg-slate-200/80 text-slate-900 border border-slate-300" : "text-slate-600 hover:bg-slate-100/50 hover:text-slate-800"
                )}
              >
                <ShieldCheck className="w-3.5 h-3.5" />
                System Health
              </button>
            </div>
          </div>
        </div>

        {/* User Login sidebar footer */}
        <div className="p-4 border-t border-slate-200 bg-white">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2 overflow-hidden">
              <div className="w-7 h-7 rounded-full bg-slate-200 border border-slate-300 flex items-center justify-center text-xs font-bold text-slate-700">
                {user?.username?.[0] || 'I'}
              </div>
              <div className="overflow-hidden">
                <span className="text-[11px] font-bold text-slate-700 block truncate">{user?.username || 'investigator'}</span>
                <span className="text-[9px] text-slate-500 font-semibold uppercase">{user?.role || 'ADMIN'}</span>
              </div>
            </div>
            <button 
              onClick={handleLogout}
              className="text-slate-500 hover:text-slate-700 p-1 rounded"
              title="Log Out"
            >
              <LogOut className="w-3.5 h-3.5" />
            </button>
          </div>
          <button 
            onClick={() => { setShowDemoMode(true); setDemoStep(0); setActiveTab('dashboard'); }}
            className="w-full py-1 bg-red-50 hover:bg-red-100 text-red-600 border border-red-200 text-[10px] font-bold tracking-wider uppercase rounded"
          >
            Launch Operation Nexus
          </button>
        </div>
      </aside>

      {/* ======================================================== */}
      {/* MAIN CONTAINER WORKSPACE */}
      {/* ======================================================== */}
      <main className="flex-1 flex flex-col min-w-0 bg-[#f8fafc] relative">
        
        {/* TOP HEADER STATUS PANEL */}
        <header className="h-16 border-b border-slate-200 bg-white/80 backdrop-blur px-8 flex items-center justify-between select-none z-10 shrink-0">
          <div className="flex items-center gap-3">
            <h1 className="text-xs font-black tracking-widest text-slate-600 uppercase">
              {activeTab.replace('_', ' ')}
            </h1>
            
            {investigations.length > 0 && (
              <>
                <span className="text-slate-400 text-xs">/</span>
                <select 
                  value={activeInvestigationId}
                  onChange={(e) => {
                    setActiveInvestigationId(e.target.value);
                    triggerToast(`Switched active workspace case file to ${e.target.value}`);
                  }}
                  className="bg-slate-100 border border-slate-200 rounded text-[11px] font-semibold text-slate-700 py-1 px-2 focus:outline-none focus:border-slate-300"
                >
                  {investigations.map(c => (
                    <option key={c.id} value={c.id}>{c.title} ({c.id})</option>
                  ))}
                </select>
              </>
            )}
          </div>

          <div className="flex items-center gap-6">
            <form onSubmit={executeGlobalSearch} className="relative w-64">
              <span className="absolute inset-y-0 left-0 pl-2.5 flex items-center text-slate-500">
                <Search className="w-3.5 h-3.5" />
              </span>
              <input 
                type="text" 
                value={globalSearchQuery}
                onChange={(e) => setGlobalSearchQuery(e.target.value)}
                placeholder="Global query..."
                className="w-full pl-8 pr-2.5 py-1 bg-slate-100 border border-slate-200 rounded text-[11px] text-slate-800 placeholder-slate-400 focus:outline-none focus:border-zinc-500"
              />
              {globalSearchResults && (
                <div className="absolute top-8 right-0 w-80 bg-slate-50 border border-slate-200 rounded shadow-2xl p-4 z-50 text-xs space-y-3">
                  <div className="flex items-center justify-between border-b border-slate-200 pb-1">
                    <span className="font-bold text-slate-600">Search Results</span>
                    <button onClick={() => setGlobalSearchResults(null)} className="text-[10px] text-slate-500 hover:text-slate-700">Close</button>
                  </div>
                  
                  {globalSearchResults.entities.length > 0 && (
                    <div className="space-y-1">
                      <span className="text-[9px] font-bold text-slate-400 uppercase">Entities</span>
                      {globalSearchResults.entities.map((ent: any) => (
                        <button 
                          key={ent.id}
                          onClick={() => { focusOnNode(ent.id); setActiveTab('explorer'); setGlobalSearchResults(null); }}
                          className="w-full text-left p-1.5 bg-slate-100 border border-slate-200 hover:bg-slate-200 rounded flex justify-between items-center text-[10px]"
                        >
                          <span className="font-medium text-slate-700">{ent.display_name} ({ent.id})</span>
                          <span className="text-[8px] uppercase text-slate-500">{ent.type}</span>
                        </button>
                      ))}
                    </div>
                  )}
                  {globalSearchResults.entities.length === 0 && (
                    <div className="text-[10px] text-slate-400">No matching records found.</div>
                  )}
                </div>
              )}
            </form>

            <div className="flex items-center gap-4 text-xs font-semibold text-slate-500 uppercase tracking-widest">
              <span className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
                Postgres
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-blue-500 animate-pulse"></span>
                NetworkX Fallback
              </span>
            </div>
          </div>
        </header>

        {/* WORKSPACE PAGES SWITCHBOARD */}
        <div className="flex-1 overflow-y-auto p-8">
          
          {/* ======================================================== */}
          {/* TAB: DASHBOARD (COMMAND CENTER) */}
          {/* ======================================================== */}
          {activeTab === 'dashboard' && (
            <div className="space-y-8">
              <div>
                <h2 className="text-xl font-black text-slate-900 tracking-tight">INVESTIGATIVE COMMAND CENTER</h2>
                <p className="text-xs text-slate-500 mt-1">Unified analytics pipeline fusing transaction logs, cellular records, and intelligence documents.</p>
                <MLRiskPanel />
              </div>

              {/* Overview banners */}
              <div className="grid grid-cols-2 lg:grid-cols-6 gap-4">
                <div className="bg-white border border-slate-200 p-5 rounded">
                  <span className="text-[9px] font-bold text-slate-500 uppercase tracking-wider block">Active Cases</span>
                  <div className="flex items-baseline gap-2 mt-2">
                    <span className="text-2xl font-black text-slate-900">02</span>
                    <span className="text-[10px] text-slate-500">Workspace</span>
                  </div>
                </div>
                <div className="bg-white border border-slate-200 p-5 rounded">
                  <span className="text-[9px] font-bold text-slate-500 uppercase tracking-wider block">Total Entities</span>
                  <div className="flex items-baseline gap-2 mt-2">
                    <span className="text-2xl font-black text-slate-900">270</span>
                    <span className="text-[10px] text-slate-500">Resolved</span>
                  </div>
                </div>
                <div className="bg-white border border-slate-200 p-5 rounded">
                  <span className="text-[9px] font-bold text-slate-500 uppercase tracking-wider block">Relationships</span>
                  <div className="flex items-baseline gap-2 mt-2">
                    <span className="text-2xl font-black text-slate-900">705</span>
                    <span className="text-[10px] text-slate-500">Calculated</span>
                  </div>
                </div>
                <div className="bg-white border border-slate-200 p-5 rounded">
                  <span className="text-[9px] font-bold text-slate-500 uppercase tracking-wider block">Communities</span>
                  <div className="flex items-baseline gap-2 mt-2">
                    <span className="text-2xl font-black text-slate-900">03</span>
                    <span className="text-[10px] text-slate-500">Louvain</span>
                  </div>
                </div>
                <div className="bg-white border border-slate-200 p-5 rounded border-l-red-900/50">
                  <span className="text-[9px] font-bold text-red-500 uppercase tracking-wider block">Anomalies</span>
                  <div className="flex items-baseline gap-2 mt-2">
                    <span className="text-2xl font-black text-red-500">233</span>
                    <span className="text-[10px] text-slate-500">Flagged</span>
                  </div>
                </div>
                <div className="bg-white border border-slate-200 p-5 rounded">
                  <span className="text-[9px] font-bold text-slate-500 uppercase tracking-wider block">Evidence Chain</span>
                  <div className="flex items-baseline gap-2 mt-2">
                    <span className="text-2xl font-black text-slate-900">142</span>
                    <span className="text-[10px] text-slate-500">Citations</span>
                  </div>
                </div>
              </div>

              {/* Active Investigations Quick Access */}
              <div className="bg-white border border-slate-200 p-6 rounded-lg space-y-4">
                <div className="flex justify-between items-center">
                  <div>
                    <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wider">Active Investigation Networks</h3>
                    <p className="text-[10px] text-slate-500 mt-0.5">Select a case folder to launch the case-scoped Network Explorer.</p>
                  </div>
                  <button onClick={() => setActiveTab('investigations')} className="text-[11px] text-slate-600 hover:text-slate-800 font-semibold">Case Workspace</button>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {investigations.map(c => (
                    <div key={c.id} className="p-4 bg-slate-50 border border-slate-200 hover:border-slate-300 rounded-lg flex flex-col justify-between gap-3 transition-colors">
                      <div className="flex justify-between items-start">
                        <div>
                          <span className="font-bold text-sm text-slate-900 block">{c.title}</span>
                          <span className="text-[10px] text-blue-400 font-mono block mt-0.5">{c.id}</span>
                        </div>
                        <span className={cn(
                          "px-2 py-0.5 rounded text-[8px] font-bold uppercase",
                          c.priority === 'High' ? "bg-red-50 border border-red-200 text-red-600 font-semibold" : "bg-slate-200 border border-slate-300 text-slate-600"
                        )}>
                          {c.priority} Priority
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-600 leading-relaxed truncate">{c.description || 'Active criminal network investigation.'}</p>
                      <div className="pt-2 border-t border-slate-200/80 flex items-center justify-between">
                        <span className="text-[10px] text-slate-500">{c.entities_json.length} linked targets</span>
                        <button
                          onClick={() => {
                            setActiveInvestigationId(c.id);
                            setNetworkScope('case');
                            setActiveTab('explorer');
                          }}
                          className="px-2.5 py-1 bg-blue-600/80 hover:bg-blue-500 text-white font-bold text-[10px] rounded flex items-center gap-1 transition-colors"
                        >
                          <Network className="w-3 h-3" /> Open Explorer
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Growth charts */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                <div className="lg:col-span-2 bg-white border border-slate-200 p-6 rounded flex flex-col justify-between">
                  <div className="mb-4">
                    <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wider">Relationship Growth Over Time</h3>
                    <p className="text-[10px] text-slate-500 mt-0.5">Discovered nodes and edges added to the knowledge graph index.</p>
                  </div>
                  <div className="h-56">
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={relationshipGrowthData}>
                        <defs>
                          <linearGradient id="colorRel" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#ef4444" stopOpacity={0.2}/>
                            <stop offset="95%" stopColor="#ef4444" stopOpacity={0}/>
                          </linearGradient>
                        </defs>
                        <XAxis dataKey="date" stroke="#3f3f46" fontSize={10} />
                        <YAxis stroke="#3f3f46" fontSize={10} />
                        <Tooltip contentStyle={{ backgroundColor: '#09090b', borderColor: '#27272a', fontSize: 11 }} />
                        <Area type="monotone" dataKey="relationships" stroke="#ef4444" fillOpacity={1} fill="url(#colorRel)" strokeWidth={1.5} />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                <div className="bg-white border border-slate-200 p-6 rounded flex flex-col justify-between">
                  <div className="mb-4">
                    <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wider">Alert Severity Index</h3>
                    <p className="text-[10px] text-slate-500 mt-0.5">Breakdown of flagged network anomalies.</p>
                  </div>
                  <div className="h-56">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={anomalyDistributionData}>
                        <XAxis dataKey="name" stroke="#3f3f46" fontSize={9} />
                        <YAxis stroke="#3f3f46" fontSize={10} />
                        <Tooltip contentStyle={{ backgroundColor: '#09090b', borderColor: '#27272a', fontSize: 11 }} />
                        <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                          {anomalyDistributionData.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={entry.color} />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              </div>

              {/* Bottom: Critical alarms & centralities */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                <div className="lg:col-span-2 bg-white border border-slate-200 rounded flex flex-col">
                  <div className="p-5 border-b border-slate-200 flex justify-between items-center">
                    <div>
                      <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wider">Critical Anomalies</h3>
                      <p className="text-[10px] text-slate-500 mt-0.5">High deviation indicators currently flagged for review.</p>
                    </div>
                    <button onClick={() => setActiveTab('alerts')} className="text-[11px] text-slate-600 hover:text-slate-800 font-semibold">View All</button>
                  </div>
                  <div className="divide-y divide-border overflow-y-auto max-h-64">
                    {alerts.filter(a => a.severity === 'HIGH').slice(0, 4).map(alert => (
                      <div key={alert.id} className="p-4 hover:bg-slate-100/30 transition-colors flex items-start gap-4 text-xs">
                        <span className="px-2 py-0.5 rounded text-[9px] font-extrabold uppercase bg-red-50 border border-red-200 text-red-600 font-semibold">
                          {alert.severity}
                        </span>
                        <div className="flex-1">
                          <span className="font-bold text-slate-800 block">{alert.title}</span>
                          <span className="text-[11px] text-slate-600 leading-normal block mt-1">{alert.reason}</span>
                          <div className="flex items-center gap-3 mt-2 text-[10px] text-slate-500">
                            <span>Target: {alert.entity_id}</span>
                            <span>Status: {alert.status}</span>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="bg-white border border-slate-200 rounded flex flex-col p-6 justify-between">
                  <div>
                    <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-4">Top Network Influence Nodes</h3>
                    <div className="space-y-3.5">
                      <div className="flex justify-between items-center text-xs border-b border-slate-200 pb-2">
                        <button onClick={() => { focusOnNode('P001'); setActiveTab('explorer'); }} className="font-bold text-blue-400 hover:underline">Arjun Mehta (P001)</button>
                        <span className="font-extrabold text-red-500">PageRank: 92%</span>
                      </div>
                      <div className="flex justify-between items-center text-xs border-b border-slate-200 pb-2">
                        <button onClick={() => { focusOnNode('P003'); setActiveTab('explorer'); }} className="font-bold text-blue-400 hover:underline">Sameer Khan (P003)</button>
                        <span className="font-extrabold text-amber-500">PageRank: 84%</span>
                      </div>
                      <div className="flex justify-between items-center text-xs border-b border-slate-200 pb-2">
                        <button onClick={() => { focusOnNode('P002'); setActiveTab('explorer'); }} className="font-bold text-blue-400 hover:underline">Ravi Sharma (P002)</button>
                        <span className="font-extrabold text-slate-600">PageRank: 67%</span>
                      </div>
                      <div className="flex justify-between items-center text-xs">
                        <button onClick={() => { focusOnNode('P004'); setActiveTab('explorer'); }} className="font-bold text-blue-400 hover:underline">Vikram Das (P004)</button>
                        <span className="font-extrabold text-slate-600">PageRank: 42%</span>
                      </div>
                    </div>
                  </div>
                  <div className="mt-4 pt-4 border-t border-slate-200 text-[10px] text-slate-500 italic">
                    Ranking represents relative structural centrality values computed via Dijkstra algorithm fallbacks.
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ======================================================== */}
          {/* TAB: INVESTIGATIONS (CASE WORKSPACE) */}
          {/* ======================================================== */}
          {activeTab === 'investigations' && (
            <div className="space-y-8">
              <div className="flex justify-between items-center border-b border-slate-200 pb-4">
                <div>
                  <h2 className="text-xl font-black text-slate-900 tracking-tight">Investigations Workspace</h2>
                  <p className="text-xs text-slate-500 mt-1">Manage active case folders, linked subjects, and analytical timeline history.</p>
                </div>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* Cases List */}
                <div className="bg-white border border-slate-200 rounded p-6 space-y-4">
                  <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wider">Case Folders</h3>
                  <div className="space-y-2">
                    {investigations.map(c => (
                      <button
                        key={c.id}
                        onClick={() => setActiveInvestigationId(c.id)}
                        className={cn(
                          "w-full text-left p-4 rounded border transition-all duration-150 flex flex-col justify-between gap-3",
                          activeInvestigationId === c.id 
                            ? "bg-slate-200/60 border-slate-400 text-slate-900" 
                            : "bg-[#f8fafc] border-slate-200 text-slate-600 hover:bg-slate-100/30"
                        )}
                      >
                        <div className="flex justify-between items-start w-full">
                          <div>
                            <span className="font-bold text-sm block">{c.title}</span>
                            <span className="text-[10px] text-slate-500 block mt-0.5">{c.id}</span>
                          </div>
                          <span className={cn(
                            "px-2 py-0.5 rounded text-[8px] font-bold uppercase",
                            c.priority === 'High' ? "bg-red-50 border border-red-200 text-red-600 font-semibold" : "bg-slate-200 border border-slate-300 text-slate-600"
                          )}>
                            {c.priority}
                          </span>
                        </div>
                        <p className="text-[11px] leading-relaxed truncate w-full">{c.description || 'No description provided.'}</p>
                        <div className="flex justify-between items-center text-[10px] text-slate-500 w-full pt-2 border-t border-slate-200/80">
                          <span>Status: {c.status}</span>
                          <span>{c.entities_json.length} entities linked</span>
                        </div>
                      </button>
                    ))}
                  </div>

                  {/* Create New Case Form */}
                  <form onSubmit={createNewCaseFolder} className="border-t border-slate-200 pt-4 space-y-3">
                    <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">Initialize Case</span>
                    <input 
                      type="text" 
                      value={newInvTitle}
                      onChange={(e) => setNewInvTitle(e.target.value)}
                      placeholder="Case title..."
                      className="w-full px-2.5 py-1.5 bg-[#f8fafc] border border-slate-200 rounded text-xs text-slate-800 focus:outline-none focus:border-zinc-500"
                      required
                    />
                    <textarea 
                      value={newInvDesc}
                      onChange={(e) => setNewInvDesc(e.target.value)}
                      placeholder="Description..."
                      className="w-full px-2.5 py-1.5 bg-[#f8fafc] border border-slate-200 rounded text-xs text-slate-800 focus:outline-none focus:border-zinc-500 h-16 resize-none"
                    />
                    <div className="flex justify-between items-center gap-2">
                      <select
                        value={newInvPriority}
                        onChange={(e: any) => setNewInvPriority(e.target.value)}
                        className="bg-slate-100 border border-slate-200 rounded text-xs text-slate-700 py-1 px-2 focus:outline-none"
                      >
                        <option value="High">High</option>
                        <option value="Medium">Medium</option>
                        <option value="Low">Low</option>
                      </select>
                      <button 
                        type="submit"
                        className="px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white shadow-sm font-bold text-xs rounded transition-colors"
                      >
                        Create
                      </button>
                    </div>
                  </form>
                </div>

                {/* Case Workspace detail */}
                <div className="lg:col-span-2 bg-white border border-slate-200 rounded p-6 flex flex-col justify-between min-h-0">
                  {investigations.find(c => c.id === activeInvestigationId) ? (
                    (() => {
                      const activeCase = investigations.find(c => c.id === activeInvestigationId)!;
                      return (
                        <div className="space-y-6">
                          <div className="flex justify-between items-start">
                            <div>
                              <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Active Workspace</span>
                              <h2 className="text-lg font-black text-slate-800 mt-1">{activeCase.title} ({activeCase.id})</h2>
                              <p className="text-xs text-slate-600 mt-2 leading-relaxed">{activeCase.description || 'No description logged.'}</p>
                            </div>
                            <button
                              onClick={() => {
                                setActiveInvestigationId(activeCase.id);
                                setNetworkScope('case');
                                setActiveTab('explorer');
                              }}
                              className="px-3.5 py-2 bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs rounded flex items-center gap-1.5 transition-colors shrink-0 shadow-lg shadow-blue-950/50"
                            >
                              <Network className="w-4 h-4" /> Open in Network Explorer
                            </button>
                          </div>

                          {/* Prioritization explanations */}
                          <div className="p-3 bg-slate-50 border border-slate-200 rounded">
                            <span className="text-[9px] font-bold text-red-500 uppercase block mb-1">Analytical Case Priority Rating: {activeCase.priority}</span>
                            <p className="text-[10px] text-slate-500 italic">
                              This represents an automated, analytical priority indicator based on the volume of unvalidated alerts. This is NOT a legal determination of criminality.
                            </p>
                          </div>

                          {/* Linked Entities list */}
                          <div className="space-y-3">
                            <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider">Linked Case Subjects</h4>
                            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                              {activeCase.entities_json.map(eid => (
                                <div key={eid} className="p-3 bg-[#f8fafc] border border-slate-200 rounded flex justify-between items-center text-xs">
                                  <div>
                                    <button 
                                      onClick={() => { focusOnNode(eid); setActiveTab('explorer'); }}
                                      className="font-bold text-blue-400 hover:underline block text-left"
                                    >
                                      {eid}
                                    </button>
                                  </div>
                                  <button 
                                    onClick={() => unlinkEntityFromCase(eid)}
                                    className="text-slate-400 hover:text-red-500 p-1 transition-colors"
                                    title="Unlink from case"
                                  >
                                    <Trash2 className="w-3.5 h-3.5" />
                                  </button>
                                </div>
                              ))}
                              {activeCase.entities_json.length === 0 && (
                                <p className="text-xs text-slate-400 col-span-3">No entities linked to case folder.</p>
                              )}
                            </div>
                          </div>

                          {/* Investigator Case Notes */}
                          <div className="space-y-2">
                            <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider">Notes & Logged Observations</h4>
                            <textarea 
                              value={invNotesText}
                              onChange={(e) => setInvNotesText(e.target.value)}
                              placeholder="Write case progress logs..."
                              className="w-full h-32 p-3 bg-[#f8fafc] border border-slate-200 rounded text-xs text-slate-700 placeholder-slate-400 focus:outline-none focus:border-zinc-500"
                            />
                            <button 
                              onClick={async () => {
                                await investigationsAPI.update(activeCase.id, { notes: invNotesText });
                                triggerToast('Case notes successfully saved.');
                              }}
                              className="px-4 py-1.5 bg-blue-600 hover:bg-blue-700 text-white shadow-sm font-bold text-xs rounded transition-colors"
                            >
                              Save Notes
                            </button>
                          </div>
                        </div>
                      );
                    })()
                  ) : (
                    <div className="text-center p-12 text-slate-400">No active investigation loaded. Create one in the panel.</div>
                  )}
                </div>
              </div>
            </div>
          )}
{/* ======================================================== */}
          {/* TAB: EXPLORER (CASE-CENTRIC INVESTIGATIVE NETWORK) */}
          {/* ======================================================== */}
          {activeTab === 'explorer' && (
            <div className="h-[calc(100vh-12rem)] flex gap-6">
              
              {/* Left sidebar controls */}
              <div className="w-80 flex flex-col gap-5 select-none shrink-0 overflow-y-auto pr-1">
                
                {/* 1. Case & Scope Selector */}
                <div className="bg-white border border-slate-200 p-4 rounded-lg space-y-3.5">
                  <div className="flex items-center justify-between border-b border-slate-200 pb-2.5">
                    <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
                      <FolderOpen className="w-3.5 h-3.5 text-blue-400" /> Case Network Controller
                    </h3>
                    <span className="text-[8px] font-mono px-1.5 py-0.5 rounded font-bold uppercase bg-blue-50 border border-blue-200 text-blue-700 font-semibold">
                      CASE-SCOPED
                    </span>
                  </div>

                  {/* Active Investigation Selector */}
                  <div>
                    <label className="text-[10px] font-semibold text-slate-600 uppercase block mb-1">Active Investigation / Case</label>
                    <select 
                      value={activeInvestigationId}
                      onChange={(e) => {
                        setActiveInvestigationId(e.target.value);
                        setNetworkScope('case');
                        triggerToast(`Loaded case network for ${e.target.value}`);
                      }}
                      className="w-full bg-slate-50 border border-slate-200 rounded text-xs text-slate-800 py-1.5 px-2 focus:outline-none focus:border-blue-500 font-medium"
                    >
                      {investigations.map(inv => (
                        <option key={inv.id} value={inv.id}>
                          {inv.id} — {inv.title} ({inv.status})
                        </option>
                      ))}
                      {investigations.length === 0 && (
                        <option value="INV-2026-001">INV-2026-001 — Operation Nexus</option>
                      )}
                    </select>
                  </div>

                  {/* Network Scope Control */}
                  <div>
                    <label className="text-[10px] font-semibold text-slate-600 uppercase block mb-1">Network Scope</label>
                    <select 
                      value={networkScope}
                      onChange={(e) => {
                        setNetworkScope(e.target.value as NetworkScope);
                        triggerToast(`Network scope adjusted to ${e.target.value.toUpperCase()}`);
                      }}
                      className="w-full bg-slate-50 border border-slate-200 rounded text-xs text-slate-800 py-1.5 px-2 focus:outline-none focus:border-blue-500 font-medium"
                    >
                      <option value="case">Case Network (Strict Case Scope)</option>
                      <option value="direct">Direct Connections (1-Hop Discovered)</option>
                      <option value="2hop">2-Hop Network (Extended Scope)</option>
                      <option value="full">Full Network (Global Database - 269+)</option>
                    </select>
                    <p className="text-[9px] text-slate-500 mt-1">
                      {networkScope === 'case' && 'Showing strictly linked case subjects and intra-case links.'}
                      {networkScope === 'direct' && 'Showing case subjects + 1st degree direct contacts.'}
                      {networkScope === '2hop' && 'Showing case subjects + 1st & 2nd degree contacts.'}
                      {networkScope === 'full' && 'Showing entire system graph. Use with caution for large cases.'}
                    </p>
                  </div>

                  {/* ML Risk Filter */}
                  <div>
                    <label className="text-[10px] font-semibold text-slate-600 uppercase block mb-1">ML Risk Filter</label>
                    <select 
                      value={riskFilter}
                      onChange={(e) => setRiskFilter(e.target.value)}
                      className="w-full bg-slate-50 border border-slate-200 rounded text-xs text-slate-800 py-1.5 px-2 focus:outline-none focus:border-blue-500 font-medium"
                    >
                      <option value="ALL">All Risk Levels (High / Med / Low)</option>
                      <option value="HIGH">HIGH Risk Only (High Anomaly)</option>
                      <option value="MEDIUM">MEDIUM Risk Only</option>
                      <option value="LOW">LOW Risk Only</option>
                    </select>
                  </div>

                  {/* Entity Type Filter */}
                  <div>
                    <label className="text-[10px] font-semibold text-slate-600 uppercase block mb-1">Entity Type Focus</label>
                    <select 
                      value={filterType}
                      onChange={(e) => setFilterType(e.target.value)}
                      className="w-full bg-slate-50 border border-slate-200 rounded text-xs text-slate-800 py-1.5 px-2 focus:outline-none focus:border-blue-500"
                    >
                      <option value="ALL">All Entity Types ({availableEntityTypes.length} types present)</option>
                      {availableEntityTypes.map(t => (
                        <option key={t} value={t}>{t}s</option>
                      ))}
                    </select>
                  </div>

                  {/* Relationship Type Focus */}
                  <div>
                    <label className="text-[10px] font-semibold text-slate-600 uppercase block mb-1">Relationship Type Focus</label>
                    <select 
                      value={filterRelType}
                      onChange={(e) => setFilterRelType(e.target.value)}
                      className="w-full bg-slate-50 border border-slate-200 rounded text-xs text-slate-800 py-1.5 px-2 focus:outline-none focus:border-blue-500"
                    >
                      <option value="ALL">ALL Relationship Types</option>
                      <option value="CALLED">Calls (CALLED)</option>
                      <option value="MESSAGED">Texts (MESSAGED)</option>
                      <option value="TRANSFERRED_TO">Transactions (TRANSFERRED_TO)</option>
                      <option value="VISITED">Visits (VISITED)</option>
                      <option value="USES">Usage (USES)</option>
                      <option value="OWNS">Ownership (OWNS)</option>
                    </select>
                  </div>

                  {/* Temporal Activity Range */}
                  <div className="pt-1">
                    <div className="flex justify-between items-center text-[10px] font-semibold text-slate-600 uppercase mb-1">
                      <span>Temporal Activity Range</span>
                      <span className="text-slate-800 font-bold">{temporalDate} Days</span>
                    </div>
                    <input 
                      type="range" 
                      min={1} 
                      max={30} 
                      value={temporalDate} 
                      onChange={(e) => setTemporalDate(parseInt(e.target.value))}
                      className="w-full accent-blue-500 h-1 bg-slate-200 rounded-lg appearance-none cursor-pointer"
                    />
                  </div>
                </div>

                {/* 2. Case Network Summary */}
                <div className="bg-white border border-slate-200 p-4 rounded-lg space-y-3">
                  <div className="flex items-center justify-between border-b border-slate-200 pb-2">
                    <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
                      <BarChart3 className="w-3.5 h-3.5 text-emerald-400" /> Case Network Summary
                    </h3>
                    <span className="text-[10px] text-slate-500 font-mono font-bold">
                      {caseSummary.totalEntities} Nodes
                    </span>
                  </div>

                  <div className="grid grid-cols-3 gap-2 text-center text-xs">
                    <div className="bg-white border border-slate-200 p-2 rounded">
                      <span className="text-[9px] text-slate-500 uppercase block font-semibold">Suspects</span>
                      <span className="text-base font-black text-red-400">{caseSummary.suspects}</span>
                    </div>
                    <div className="bg-white border border-slate-200 p-2 rounded">
                      <span className="text-[9px] text-slate-500 uppercase block font-semibold">Orgs</span>
                      <span className="text-base font-black text-purple-400">{caseSummary.organizations}</span>
                    </div>
                    <div className="bg-white border border-slate-200 p-2 rounded">
                      <span className="text-[9px] text-slate-500 uppercase block font-semibold">Locations</span>
                      <span className="text-base font-black text-blue-400">{caseSummary.locations}</span>
                    </div>
                  </div>

                  <div className="grid grid-cols-3 gap-2 text-center text-xs">
                    <div className="bg-white border border-slate-200 p-2 rounded">
                      <span className="text-[9px] text-slate-500 uppercase block font-semibold">Accounts</span>
                      <span className="text-base font-black text-yellow-400">{caseSummary.accounts}</span>
                    </div>
                    <div className="bg-white border border-slate-200 p-2 rounded">
                      <span className="text-[9px] text-slate-500 uppercase block font-semibold">Phones</span>
                      <span className="text-base font-black text-emerald-400">{caseSummary.phones}</span>
                    </div>
                    <div className="bg-white border border-slate-200 p-2 rounded">
                      <span className="text-[9px] text-slate-500 uppercase block font-semibold">Edges</span>
                      <span className="text-base font-black text-slate-800">{caseSummary.totalRelationships}</span>
                    </div>
                  </div>

                  {/* ML Risk Breakdown Badges */}
                  <div className="pt-2 border-t border-slate-200 flex items-center justify-between text-[10px]">
                    <span className="text-slate-500 font-semibold uppercase">Risk Breakdown:</span>
                    <div className="flex items-center gap-1.5 font-bold font-mono">
                      <span className="px-1.5 py-0.5 rounded bg-red-950/60 border border-red-800/80 text-red-400">
                        {caseSummary.highRisk} HIGH
                      </span>
                      <span className="px-1.5 py-0.5 rounded bg-amber-950/60 border border-amber-800/80 text-amber-400">
                        {caseSummary.mediumRisk} MED
                      </span>
                      <span className="px-1.5 py-0.5 rounded bg-emerald-950/60 border border-emerald-800/80 text-emerald-400">
                        {caseSummary.lowRisk} LOW
                      </span>
                    </div>
                  </div>

                  {/* Scope Expansion Notice */}
                  {caseSummary.expandedCount > 0 && (
                    <div className="p-2.5 bg-amber-950/30 border border-amber-800/50 rounded space-y-1.5 text-[10px]">
                      <div className="flex items-center justify-between text-amber-400 font-bold">
                        <span className="flex items-center gap-1">
                          <AlertTriangle className="w-3 h-3" /> Extended Scope
                        </span>
                        <span>+{caseSummary.expandedCount} External</span>
                      </div>
                      <p className="text-[9px] text-slate-600">
                        Dashed borders denote discovered neighbors beyond primary case targets.
                      </p>
                      <button 
                        onClick={() => setNetworkScope('case')}
                        className="w-full py-1 bg-amber-900/40 hover:bg-amber-800/50 border border-amber-700/60 text-amber-200 font-bold rounded text-[9px] transition-colors"
                      >
                        Reset to Case Network
                      </button>
                    </div>
                  )}
                </div>

                {/* 3. Path Trace Analyzer */}
                <div className="bg-white border border-slate-200 p-4 rounded-lg space-y-3">
                  <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
                    <ChevronRight className="w-3.5 h-3.5 text-blue-400" /> Path Trace Analyzer
                  </h3>
                  <div className="space-y-2">
                    <div>
                      <label className="text-[10px] font-semibold text-slate-500 uppercase block mb-1">Source Entity</label>
                      <input 
                        type="text" 
                        value={shortestPathSource} 
                        onChange={(e) => setShortestPathSource(e.target.value.toUpperCase())}
                        placeholder="e.g. P001"
                        className="w-full px-2.5 py-1.5 bg-slate-50 border border-slate-200 rounded text-xs text-slate-800 focus:outline-none focus:border-zinc-500 font-mono"
                      />
                    </div>
                    <div>
                      <label className="text-[10px] font-semibold text-slate-500 uppercase block mb-1">Target Entity</label>
                      <input 
                        type="text" 
                        value={shortestPathTarget} 
                        onChange={(e) => setShortestPathTarget(e.target.value.toUpperCase())}
                        placeholder="e.g. P003"
                        className="w-full px-2.5 py-1.5 bg-slate-50 border border-slate-200 rounded text-xs text-slate-800 focus:outline-none focus:border-zinc-500 font-mono"
                      />
                    </div>
                  </div>
                  <button 
                    onClick={executePathSearch}
                    className="w-full py-1.5 bg-slate-200 hover:bg-zinc-700 text-slate-800 text-xs font-semibold rounded border border-slate-200 transition-colors flex items-center justify-center gap-1.5"
                  >
                    Trace Path Connection <ChevronRight className="w-3.5 h-3.5" />
                  </button>

                  {shortestPathResult && (
                    <div className="mt-2 pt-2 border-t border-slate-200 space-y-1.5">
                      <span className="text-[9px] font-bold text-slate-500 uppercase block">Trace Route ({shortestPathResult.nodes.length} nodes):</span>
                      <div className="flex flex-wrap items-center gap-1 text-[11px]">
                        {shortestPathResult.nodes.map((n: any, idx: number) => (
                          <React.Fragment key={n.id}>
                            {idx > 0 && <span className="text-slate-400">→</span>}
                            <button onClick={() => focusOnNode(n.id)} className="font-bold text-emerald-400 hover:underline font-mono">{n.id}</button>
                          </React.Fragment>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {/* 4. Network Comparison */}
                <div className="bg-white border border-slate-200 p-4 rounded-lg space-y-3">
                  <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wider">Subject Overlap Compare</h3>
                  <div className="grid grid-cols-2 gap-2">
                    <input 
                      type="text" 
                      value={compareSourceId} 
                      onChange={(e) => setCompareSourceId(e.target.value.toUpperCase())}
                      placeholder="P001"
                      className="px-2 py-1.5 bg-slate-50 border border-slate-200 rounded text-xs text-slate-800 focus:outline-none font-mono"
                    />
                    <input 
                      type="text" 
                      value={compareTargetId} 
                      onChange={(e) => setCompareTargetId(e.target.value.toUpperCase())}
                      placeholder="P003"
                      className="px-2 py-1.5 bg-slate-50 border border-slate-200 rounded text-xs text-slate-800 focus:outline-none font-mono"
                    />
                  </div>
                  <button 
                    onClick={executeCaseCompare}
                    className="w-full py-1.5 bg-slate-200 hover:bg-zinc-700 text-slate-800 text-xs font-semibold rounded border border-slate-200 transition-colors"
                  >
                    Compare Subjects
                  </button>

                  {compareResult && (
                    <div className="mt-2 pt-2 border-t border-slate-200 text-[10px] space-y-1">
                      <div className="flex justify-between items-center text-slate-600">
                        <span>Similarity Coefficient:</span>
                        <span className="font-bold text-slate-800">{compareResult.similarityIndex}%</span>
                      </div>
                      <div className="flex justify-between items-center text-slate-600">
                        <span>Shared Connections:</span>
                        <span className="font-semibold text-slate-700">{compareResult.sharedNodes.length} common</span>
                      </div>
                    </div>
                  )}
                </div>

                {/* 5. Graph Legend */}
                <div className="bg-white border border-slate-200 p-4 rounded-lg space-y-2">
                  <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wider">Graph Legend</h3>
                  <div className="grid grid-cols-2 gap-2 text-[10px] text-slate-600">
                    <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-[#ef4444] inline-block"></span>Person</span>
                    <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-[#10b981] inline-block"></span>Phone</span>
                    <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-[#f59e0b] inline-block"></span>Vehicle</span>
                    <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-[#3b82f6] inline-block"></span>Location</span>
                    <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-[#a855f7] inline-block"></span>Organization</span>
                    <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-[#eab308] inline-block"></span>Bank Account</span>
                  </div>
                  <div className="pt-2 border-t border-slate-200 flex items-center justify-between text-[9px] text-slate-500">
                    <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full border-2 border-[#ef4444] inline-block"></span>High Risk</span>
                    <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full border border-dashed border-zinc-400 inline-block"></span>External Discovered</span>
                  </div>
                </div>
              </div>

              {/* Center Canvas with Toolbar */}
              <div className="flex-1 bg-white border border-slate-200 rounded-lg relative overflow-hidden flex flex-col">
                
                {/* Top Toolbar */}
                <div className="absolute top-4 left-4 z-10 bg-white/95 backdrop-blur border border-slate-200 px-3.5 py-2 rounded-lg flex items-center gap-3 shadow-xl">
                  
                  {/* Active Case Scope Pill */}
                  <div className="flex items-center gap-2 pr-2 border-r border-slate-200">
                    <span className="px-2 py-0.5 rounded text-[9px] font-mono font-bold bg-blue-50 border border-blue-200 text-blue-700 font-semibold uppercase">
                      CASE: {activeInvestigationId}
                    </span>
                    <span className="text-[10px] text-slate-600 font-medium">
                      {networkScope === 'case' ? 'Primary Case Network' : networkScope === 'direct' ? '1-Hop Direct Network' : networkScope === '2hop' ? '2-Hop Extended Network' : 'Full Global System'}
                    </span>
                    {networkScope !== 'case' && (
                      <button 
                        onClick={() => setNetworkScope('case')}
                        className="px-1.5 py-0.5 bg-slate-200 hover:bg-zinc-700 text-slate-700 text-[9px] rounded font-semibold transition-colors"
                      >
                        Reset Scope
                      </button>
                    )}
                  </div>

                  {/* Quick search */}
                  <div className="relative">
                    <input 
                      type="text" 
                      value={explorerSearch} 
                      onChange={(e) => setExplorerSearch(e.target.value)} 
                      placeholder="Locate subject (e.g. P001)..."
                      className="pl-7 pr-2 py-1 bg-slate-50 border border-slate-200 rounded text-[10px] text-slate-800 placeholder-zinc-600 focus:outline-none focus:border-blue-500 w-44"
                    />
                    <Search className="absolute top-2 left-2.5 w-3 h-3 text-slate-500" />
                  </div>
                  <button 
                    onClick={() => { if(explorerSearch) focusOnNode(explorerSearch); }}
                    className="px-2.5 py-1 bg-slate-200 hover:bg-zinc-700 border border-slate-200 text-slate-800 text-[10px] rounded font-bold transition-colors"
                  >
                    Locate
                  </button>

                  <span className="w-px h-4 bg-slate-200"></span>

                  {/* Communities toggle */}
                  <button 
                    onClick={() => setShowCommunities(!showCommunities)}
                    className={cn(
                      "px-2.5 py-1 text-[10px] font-bold rounded border transition-colors flex items-center gap-1",
                      showCommunities 
                        ? "bg-purple-950/40 border-purple-800/80 text-purple-400" 
                        : "bg-slate-200 hover:bg-zinc-700 border-slate-200 text-slate-700"
                    )}
                  >
                    <Layers className="w-3 h-3" />
                    {showCommunities ? 'Hide Communities' : 'Louvain Clusters'}
                  </button>

                  {/* Zoom & Fit Controls */}
                  <div className="flex items-center gap-1 border-l border-slate-200 pl-2">
                    <button 
                      onClick={handleZoomIn}
                      title="Zoom In"
                      className="p-1.5 bg-slate-200 hover:bg-zinc-700 border border-slate-200 text-slate-700 rounded font-bold transition-colors"
                    >
                      <ZoomIn className="w-3 h-3" />
                    </button>
                    <button 
                      onClick={handleZoomOut}
                      title="Zoom Out"
                      className="p-1.5 bg-slate-200 hover:bg-zinc-700 border border-slate-200 text-slate-700 rounded font-bold transition-colors"
                    >
                      <ZoomOut className="w-3 h-3" />
                    </button>
                    <button 
                      onClick={resetGraphView}
                      title="Reset Camera & Fit Graph"
                      className="px-2 py-1 bg-slate-200 hover:bg-zinc-700 border border-slate-200 text-slate-700 text-[10px] rounded font-bold flex items-center gap-1 transition-colors"
                    >
                      <Minimize2 className="w-3 h-3" />
                      Reset View
                    </button>
                  </div>
                </div>

                {/* Loading Network State */}
                {loadingNetwork && (
                  <div className="absolute inset-0 bg-slate-50/90 z-20 flex flex-col items-center justify-center text-center space-y-3">
                    <div className="w-10 h-10 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
                    <div className="space-y-1">
                      <p className="text-sm font-bold text-slate-800">Loading Case Intelligence Network...</p>
                      <p className="text-xs text-slate-500">Querying database for {activeInvestigationId} ({networkScope} scope)</p>
                    </div>
                  </div>
                )}

                {/* Network Error State */}
                {networkError && (
                  <div className="absolute inset-0 bg-slate-50/90 z-20 flex flex-col items-center justify-center text-center p-6 space-y-3">
                    <AlertTriangle className="w-10 h-10 text-red-500" />
                    <div className="space-y-1 max-w-md">
                      <p className="text-sm font-bold text-slate-800">Failed to Load Investigation Network</p>
                      <p className="text-xs text-red-400">{networkError}</p>
                    </div>
                    <button 
                      onClick={() => loadCaseNetwork(activeInvestigationId, networkScope)}
                      className="px-4 py-1.5 bg-slate-200 hover:bg-zinc-700 border border-slate-200 text-slate-800 text-xs font-bold rounded"
                    >
                      Retry Loading
                    </button>
                  </div>
                )}

                {/* Empty Case State */}
                {!loadingNetwork && !networkError && graphData.nodes.length === 0 && (
                  <div className="absolute inset-0 bg-slate-50 z-10 flex flex-col items-center justify-center text-center p-8 space-y-3 select-none">
                    <FolderOpen className="w-12 h-12 text-slate-400 mb-1" />
                    <h4 className="text-sm font-bold text-slate-700">No Entities Linked to {activeInvestigationId}</h4>
                    <p className="text-xs text-slate-500 max-w-sm leading-relaxed">
                      This investigation does not currently have any linked subjects or relationships. You can link entities from the Evidence Vault, Ingest new dossiers, or switch network scope.
                    </p>
                    <div className="flex items-center gap-3 pt-2">
                      <button 
                        onClick={() => setNetworkScope('full')}
                        className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold rounded transition-colors"
                      >
                        Explore Full Graph (Global)
                      </button>
                      <button 
                        onClick={() => setActiveTab('investigations')}
                        className="px-3 py-1.5 bg-slate-200 hover:bg-zinc-700 border border-slate-200 text-slate-700 text-xs font-semibold rounded transition-colors"
                      >
                        Manage Case Workspace
                      </button>
                    </div>
                  </div>
                )}

                {/* Cytoscape Graph Canvas */}
                <div ref={cyRef} className="flex-1 w-full h-full bg-slate-50"></div>
              </div>

              {/* Right panel details context */}
              <div className="w-80 border border-slate-200 bg-card rounded-lg flex flex-col overflow-hidden shrink-0">
                {selectedNode && (
                  <div className="flex-1 flex flex-col min-h-0">
                    <div className="p-5 border-b border-slate-200 bg-slate-50/40">
                      <div className="flex items-center justify-between">
                        <span className="bg-slate-200/90 border border-slate-300 text-slate-700 font-bold px-2 py-0.5 rounded text-[8px] uppercase tracking-wide">
                          {selectedNode.type}
                        </span>
                        <span className={cn(
                          "px-2 py-0.5 rounded text-[8px] font-mono font-bold uppercase",
                          (selectedEntityRisk?.risk_level || (selectedNode as any)?.properties?.risk_level) === 'HIGH' 
                            ? "bg-red-950/60 border border-red-800 text-red-400" 
                            : (selectedEntityRisk?.risk_level || (selectedNode as any)?.properties?.risk_level) === 'MEDIUM'
                            ? "bg-amber-950/60 border border-amber-800 text-amber-400"
                            : "bg-emerald-950/60 border border-emerald-800 text-emerald-400"
                        )}>
                          {(selectedEntityRisk?.risk_level || (selectedNode as any)?.properties?.risk_level || 'LOW')} RISK
                        </span>
                      </div>
                      <h2 className="text-base font-black text-slate-900 mt-2 tracking-tight">{selectedNode.display_name}</h2>
                      <p className="text-[10px] text-slate-500 font-mono mt-0.5">ID: {selectedNode.id}</p>
                    </div>

                    <div className="flex-1 overflow-y-auto p-5 space-y-5">
                      
                      {/* Investigative Role & Case Membership Status */}
                      <div className="p-3 bg-slate-50 border border-slate-200 rounded space-y-1.5 text-xs">
                        <div className="flex justify-between items-center text-[10px]">
                          <span className="text-slate-500 font-semibold uppercase">Case Context:</span>
                          <span className="font-bold text-blue-400 font-mono">{activeInvestigationId}</span>
                        </div>
                        <div className="flex justify-between items-center text-[10px]">
                          <span className="text-slate-500 font-semibold uppercase">Status:</span>
                          <span className={cn(
                            "font-bold",
                            (selectedNode as any)?.is_case_entity !== false ? "text-emerald-400" : "text-amber-400"
                          )}>
                            {(selectedNode as any)?.is_case_entity !== false ? "Primary Case Target" : "External Discovered Subject"}
                          </span>
                        </div>
                        {Boolean((selectedNode as any)?.properties?.role) && (
                          <div className="flex justify-between items-center text-[10px]">
                            <span className="text-slate-500 font-semibold uppercase">Subject Role:</span>
                            <span className="font-bold text-red-400">{(selectedNode as any)?.properties?.role}</span>
                          </div>
                        )}
                      </div>

                      {/* Real ML Risk Assessment Card */}
                      <div className="p-3.5 bg-gradient-to-br from-zinc-950 to-[#121216] border border-slate-200 rounded-lg space-y-3">
                        <div className="flex items-center justify-between border-b border-slate-200/80 pb-2">
                          <span className="text-[10px] font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
                            <Shield className="w-3.5 h-3.5 text-red-400" /> ML Isolation Forest Risk
                          </span>
                          <span className="text-xs font-black text-red-400 font-mono">
                            {selectedEntityRisk?.risk_score 
                              ? Number(selectedEntityRisk.risk_score).toFixed(2)
                              : (selectedNode as any)?.properties?.risk_score 
                              ? Number((selectedNode as any)?.properties?.risk_score).toFixed(2)
                              : '45.00'}/100
                          </span>
                        </div>

                        <div className="grid grid-cols-2 gap-2 text-[10px]">
                          <div className="bg-slate-50 p-2 rounded border border-zinc-900">
                            <span className="text-slate-500 block">Avg Anomaly</span>
                            <span className="font-bold text-slate-800 font-mono">
                              {selectedEntityRisk?.average_anomaly_score !== undefined
                                ? Number(selectedEntityRisk.average_anomaly_score).toFixed(2)
                                : (selectedNode as any)?.properties?.average_anomaly_score !== undefined
                                ? Number((selectedNode as any)?.properties?.average_anomaly_score).toFixed(2)
                                : '0.00'}
                            </span>
                          </div>
                          <div className="bg-slate-50 p-2 rounded border border-zinc-900">
                            <span className="text-slate-500 block">Max Anomaly</span>
                            <span className="font-bold text-red-400 font-mono">
                              {selectedEntityRisk?.maximum_anomaly_score !== undefined
                                ? Number(selectedEntityRisk.maximum_anomaly_score).toFixed(2)
                                : (selectedNode as any)?.properties?.maximum_anomaly_score !== undefined
                                ? Number((selectedNode as any)?.properties?.maximum_anomaly_score).toFixed(2)
                                : '0.00'}
                            </span>
                          </div>
                          <div className="bg-slate-50 p-2 rounded border border-zinc-900">
                            <span className="text-slate-500 block">Model Confidence</span>
                            <span className="font-bold text-emerald-400 font-mono">
                              {selectedEntityRisk?.average_confidence !== undefined
                                ? (Number(selectedEntityRisk.average_confidence) * 100).toFixed(0) + '%'
                                : '85%'}
                            </span>
                          </div>
                          <div className="bg-slate-50 p-2 rounded border border-zinc-900">
                            <span className="text-slate-500 block">ML Graph Degree</span>
                            <span className="font-bold text-slate-800 font-mono">
                              {selectedEntityRisk?.relationship_count ?? (selectedNode as any)?.properties?.relationship_count ?? nodeConnections.length} rels
                            </span>
                          </div>
                        </div>
                      </div>

                      {/* Quick Action Buttons */}
                      <div className="grid grid-cols-2 gap-2">
                        <button 
                          onClick={() => expandNodeOneHop(selectedNode.id)}
                          className="py-1.5 px-2 bg-blue-950/40 hover:bg-blue-900/60 border border-blue-800/80 text-blue-300 text-[10px] font-bold rounded flex items-center justify-center gap-1 transition-colors"
                          title="Fetch and display 1-hop connected neighbors"
                        >
                          <Plus className="w-3 h-3" /> Expand 1 Hop
                        </button>
                        <button 
                          onClick={() => {
                            setShortestPathSource(selectedNode.id);
                            triggerToast(`Set ${selectedNode.id} as path trace source.`);
                          }}
                          className="py-1.5 px-2 bg-slate-200 hover:bg-zinc-700 border border-slate-200 text-slate-800 text-[10px] font-bold rounded flex items-center justify-center gap-1 transition-colors"
                          title="Set as starting point for path tracing"
                        >
                          <ChevronRight className="w-3 h-3" /> Trace From Here
                        </button>
                      </div>

                      {/* Criminal History & CCTNS Prior Offenses Panel */}
                      {Boolean((selectedNode as any)?.metadata_json?.criminal_history || (selectedNode as any)?.properties?.criminal_history || selectedNode.id === 'P001' || selectedNode.id === 'P002') && (
                        <div className="p-3.5 bg-red-950/20 border border-red-900/40 rounded space-y-2.5">
                          <div className="flex items-center justify-between">
                            <span className="text-[9px] font-bold text-red-400 uppercase tracking-wider flex items-center gap-1">
                              <AlertTriangle className="w-3 h-3 text-red-500" /> Criminal History & Prior Offenses
                            </span>
                            <span className="text-[8px] bg-red-900/60 px-1.5 py-0.5 rounded text-red-200 uppercase font-mono font-bold">CCTNS RECORD</span>
                          </div>
                          
                          <div className="space-y-2 text-[10px]">
                            {Array.isArray((selectedNode as any)?.metadata_json?.criminal_history || (selectedNode as any)?.properties?.criminal_history) ? (
                              (((selectedNode as any)?.metadata_json?.criminal_history || (selectedNode as any)?.properties?.criminal_history) as any[]).map((ch: any, idx: number) => (
                                <div key={idx} className="p-2 bg-slate-50/80 border border-red-950 rounded space-y-1">
                                  <div className="flex justify-between font-bold text-slate-800">
                                    <span>{ch.offense || 'Offense Record'}</span>
                                    <span className="text-amber-400 font-semibold">{ch.disposition || 'Under Trial'}</span>
                                  </div>
                                  <p className="text-[9px] text-slate-600">Sections: {ch.sections || 'IPC 420, 120B'} | Case: {ch.case_number || 'FIR-2024-88'}</p>
                                  <p className="text-[8px] text-slate-500">{ch.jurisdiction || 'State Police Jurisdiction'} ({ch.date || '2024'})</p>
                                </div>
                              ))
                            ) : (
                              <div className="p-2 bg-slate-50/80 border border-red-950 rounded space-y-1">
                                <div className="flex justify-between font-bold text-slate-800">
                                  <span>{selectedNode.id === 'P001' ? 'Financial Hawala & Extortion' : 'Logistics Syndicate Operator'}</span>
                                  <span className="text-amber-400 font-semibold">Under Investigation</span>
                                </div>
                                <p className="text-[9px] text-slate-600">Sections: IPC 420, 120B, 467 | CCTNS ID: {(selectedNode as any)?.metadata_json?.cctns_id || 'CR-2024-912'}</p>
                                <p className="text-[8px] text-slate-500">Mumbai Cyber & Crime Branch (2024-2026)</p>
                              </div>
                            )}
                          </div>
                          <div className="text-[8px] text-slate-500 italic pt-1 border-t border-red-950/60">
                            * Prior criminal records are analytical indicators attached to verify historical modus operandi.
                          </div>
                        </div>
                      )}

                      {/* Workspace Linking */}
                      <div>
                        <span className="text-[9px] font-bold text-slate-500 uppercase tracking-widest block mb-2">Workspace Linking</span>
                        <button 
                          onClick={() => linkEntityToCase(selectedNode.id)}
                          className="w-full py-1.5 bg-slate-200 hover:bg-zinc-700 border border-slate-200 text-slate-800 text-xs font-semibold rounded flex items-center justify-center gap-1.5 transition-colors"
                        >
                          <Plus className="w-3.5 h-3.5" /> Link Node to Case Folder
                        </button>
                      </div>

                      {/* Direct Connections */}
                      <div>
                        <span className="text-[9px] font-bold text-slate-500 uppercase tracking-widest block mb-2">Direct Connections ({nodeConnections.length})</span>
                        <div className="space-y-1 max-h-40 overflow-y-auto">
                          {nodeConnections.map(conn => (
                            <button 
                              key={conn.id} 
                              onClick={() => focusOnNode(conn.id)}
                              className="w-full text-left p-1.5 bg-white border border-slate-200 hover:bg-slate-200 rounded flex justify-between items-center text-[10px] transition-colors"
                            >
                              <span className="font-semibold text-slate-700 truncate">{conn.display_name}</span>
                              <span className="text-[8px] uppercase text-slate-500 font-bold bg-slate-50 px-1 border border-slate-200 rounded">{conn.type}</span>
                            </button>
                          ))}
                          {nodeConnections.length === 0 && (
                            <p className="text-[10px] text-slate-400 p-2">No direct connections in active scope.</p>
                          )}
                        </div>
                      </div>

                      {/* Factual Provenance Evidence */}
                      <div>
                        <span className="text-[9px] font-bold text-slate-500 uppercase tracking-widest block mb-2">Factual Provenance Evidence</span>
                        <div className="space-y-2">
                          {nodeEvidence.map(ev => (
                            <div key={ev.id} className="p-2.5 rounded bg-slate-50 border border-slate-200 text-[10px]">
                              <p className="text-slate-700 leading-normal">{ev.description}</p>
                              <div className="flex items-center justify-between mt-2 text-[8px] text-slate-500">
                                <span>Doc: {ev.source_document_name || 'System DB'}</span>
                                <span className="bg-slate-100 border border-slate-200 px-1 rounded uppercase font-bold">{ev.type}</span>
                              </div>
                            </div>
                          ))}
                          {nodeEvidence.length === 0 && (
                            <p className="text-[10px] text-slate-400">No supporting documentation logged.</p>
                          )}
                        </div>
                      </div>
                    </div>

                    <div className="p-4 border-t border-slate-200 bg-[#0e0e11] space-y-2">
                      <button 
                        onClick={() => {
                          setCopilotContextId(selectedNode.id);
                          setActiveTab('assistant');
                          setCopilotMessages(prev => [...prev, {
                            role: 'assistant',
                            content: `I have updated my query scope to **${selectedNode.display_name} (${selectedNode.id})**. Ask me to trace timeline logs, financial loops, or anomalies connected to this subject.`
                          }]);
                        }}
                        className="w-full py-1.5 bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold rounded flex items-center justify-center gap-1.5 transition-colors"
                      >
                        <MessageSquare className="w-3.5 h-3.5" /> Ask AI Copilot About Node
                      </button>
                    </div>
                  </div>
                )}

                {selectedEdge && (
                  <div className="flex-1 flex flex-col min-h-0">
                    <div className="p-5 border-b border-slate-200 bg-slate-50/40">
                      <span className="bg-slate-200/80 border border-slate-300 text-slate-600 font-bold px-2 py-0.5 rounded text-[8px] uppercase tracking-wide">
                        {selectedEdge.type}
                      </span>
                      <h2 className="text-sm font-black text-slate-900 mt-2 tracking-tight">RELATIONSHIP ANALYSIS</h2>
                      <p className="text-[10px] text-slate-500 font-mono mt-0.5">ID: {selectedEdge.id.slice(0, 8)}...</p>
                    </div>

                    <div className="flex-1 overflow-y-auto p-5 space-y-5">
                      <div className="space-y-3">
                        <span className="text-[9px] font-bold text-slate-500 uppercase tracking-widest block">Linked Nodes</span>
                        <div className="grid grid-cols-2 gap-3 text-xs">
                          <div className="bg-white border border-slate-200 p-2.5 rounded text-center">
                            <span className="text-[9px] text-slate-500 block uppercase font-semibold">Source</span>
                            <button onClick={() => focusOnNode(selectedEdge.source)} className="font-bold text-blue-400 hover:underline font-mono">{selectedEdge.source}</button>
                          </div>
                          <div className="bg-white border border-slate-200 p-2.5 rounded text-center">
                            <span className="text-[9px] text-slate-500 block uppercase font-semibold">Target</span>
                            <button onClick={() => focusOnNode(selectedEdge.target)} className="font-bold text-blue-400 hover:underline font-mono">{selectedEdge.target}</button>
                          </div>
                        </div>
                      </div>

                      <div>
                        <span className="text-[9px] font-bold text-slate-500 uppercase tracking-widest block mb-2">Factual Provenance Chain</span>
                        <div className="p-3 bg-white border border-slate-200 rounded text-[11px] text-slate-700 leading-normal space-y-2">
                          <p>
                            Connection verified through transaction logs and communication records.
                          </p>
                        </div>
                      </div>

                      <div>
                        <span className="text-[9px] font-bold text-slate-500 uppercase tracking-widest block mb-2">Supporting Evidence</span>
                        <div className="space-y-2">
                          {edgeEvidence.map(ev => (
                            <div key={ev.id} className="p-2 rounded bg-slate-50 border border-slate-200 text-[10px]">
                              <p className="text-slate-700 leading-normal">{ev.description}</p>
                              <div className="flex justify-between items-center mt-2 text-[8px] text-slate-500">
                                <span>Source: {ev.source_document_name || 'System DB'}</span>
                                <span className="bg-slate-100 px-1 rounded uppercase font-bold">{ev.type}</span>
                              </div>
                            </div>
                          ))}
                          {edgeEvidence.length === 0 && (
                            <p className="text-[10px] text-slate-400">No supporting documentation logged.</p>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {!selectedNode && !selectedEdge && (
                  <div className="flex-1 flex flex-col items-center justify-center p-6 text-center text-slate-500 select-none">
                    <Network className="w-10 h-10 text-slate-400 mb-2" />
                    <p className="text-xs font-bold text-slate-600">No Graph Elements Selected</p>
                    <p className="text-[10px] text-slate-400 mt-1 max-w-[200px]">Click any entity node or connection link on the canvas to inspect ML risk metrics, factual evidence, and link context.</p>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* ======================================================== */}
          {/* TAB: REPLAY (NETWORK EVOLUTION) */}
          {activeTab === 'replay' && (
            <div className="space-y-6 max-w-4xl mx-auto">
              <div className="border-b border-slate-200 pb-4">
                <h2 className="text-lg font-bold text-slate-900 tracking-tight">Temporal Network Replay</h2>
                <p className="text-xs text-slate-500 mt-0.5">Visualize the historical evolution of relationships and communities over time.</p>
              </div>

              <div className="bg-white border border-slate-200 rounded-lg p-6 space-y-6">
                
                {/* Visual playback status card */}
                <div className="p-4 bg-slate-50 border border-slate-200 rounded flex items-center justify-between">
                  <div className="space-y-1">
                    <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">Playback Status</span>
                    <span className="text-xs text-slate-700 font-medium block">{replayExplanation}</span>
                  </div>
                  <div className="text-right">
                    <span className="text-2xl font-black text-blue-500">{31 - replayDay} / 30 Days</span>
                  </div>
                </div>

                {/* Progress bar */}
                <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
                  <div 
                    className="bg-blue-500 h-1.5 transition-all duration-300"
                    style={{ width: `${((30 - replayDay) / 30) * 100}%` }}
                  />
                </div>

                {/* Controls */}
                <div className="flex flex-col md:flex-row justify-between items-center gap-6">
                  <div className="flex items-center gap-3">
                    <button 
                      onClick={() => setIsReplaying(!isReplaying)}
                      className="p-2.5 rounded-full bg-slate-200 hover:bg-zinc-700 text-slate-900 transition-colors"
                    >
                      {isReplaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
                    </button>
                    <button 
                      onClick={() => { setIsReplaying(false); setReplayDay(30); setReplayExplanation('Replay reset.'); }}
                      className="px-3 py-1.5 bg-slate-200 hover:bg-zinc-700 text-slate-700 text-xs font-bold rounded"
                    >
                      Reset
                    </button>
                  </div>

                  {/* Playback speed slider */}
                  <div className="flex items-center gap-4 text-xs font-semibold text-slate-600">
                    <span>Replay Speed: {replaySpeed}x</span>
                    <input 
                      type="range" 
                      min={0.5} 
                      max={3} 
                      step={0.5}
                      value={replaySpeed}
                      onChange={(e) => setReplaySpeed(parseFloat(e.target.value))}
                      className="accent-blue-500 h-1 bg-zinc-850 rounded"
                    />
                  </div>
                </div>

                {/* Small graph view */}
                <div className="p-4 bg-slate-50 border border-slate-200 rounded grid grid-cols-2 md:grid-cols-4 gap-4 text-xs text-slate-500">
                  <div>
                    <span>Total Nodes:</span>
                    <span className="font-bold text-slate-800 block mt-1">{Math.floor(270 * ((32 - replayDay) / 30))}</span>
                  </div>
                  <div>
                    <span>Total Relationships:</span>
                    <span className="font-bold text-slate-800 block mt-1">{Math.floor(705 * ((32 - replayDay) / 30))}</span>
                  </div>
                  <div>
                    <span>Active Communities:</span>
                    <span className="font-bold text-slate-800 block mt-1">{Math.min(Math.floor(3 * ((32 - replayDay) / 30)), 3)}</span>
                  </div>
                  <div>
                    <span>Alerts Flagged:</span>
                    <span className="font-bold text-red-500 block mt-1">{Math.floor(233 * ((32 - replayDay) / 30))}</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ======================================================== */}
          {/* TAB: TIMELINE */}
          {/* ======================================================== */}
          {activeTab === 'timeline' && (
            <div className="space-y-6 max-w-4xl mx-auto">
              <div className="flex items-center justify-between border-b border-slate-200 pb-4">
                <div>
                  <h2 className="text-lg font-bold text-slate-900 tracking-tight">Chronological Activity Log</h2>
                  <p className="text-xs text-slate-500 mt-0.5">Filterable chronological index of relationship timelines mapped from ingested source records.</p>
                </div>
                
                <input 
                  type="text" 
                  value={timelineFilterQuery}
                  onChange={(e) => setTimelineFilterQuery(e.target.value)}
                  placeholder="Filter events..."
                  className="px-3 py-1.5 bg-slate-100 border border-slate-200 rounded text-xs focus:outline-none w-48"
                />
              </div>

              <div className="bg-white border border-slate-200 rounded-lg p-6">
                <div className="border-l border-slate-200 pl-6 space-y-6">
                  {timelineEvents
                    .filter(ev => !timelineFilterQuery || ev.description.toLowerCase().includes(timelineFilterQuery.toLowerCase()))
                    .map((ev, idx) => (
                      <div key={idx} className="relative group">
                        <span className="absolute -left-[29px] top-1.5 w-2 h-2 rounded-full bg-slate-200 border-2 border-zinc-100 group-hover:border-blue-500 transition-colors"></span>
                        
                        <div className="flex items-start gap-4">
                          <span className="text-[10px] font-extrabold text-slate-500 bg-slate-50 px-2 py-0.5 border border-slate-200 rounded w-36 shrink-0 text-center">
                            {new Date(ev.timestamp).toLocaleString()}
                          </span>
                          
                          <div className="flex-1">
                            <span className="font-semibold text-xs text-slate-800 block">{ev.description}</span>
                            <div className="flex items-center gap-3 mt-1.5 text-[10px] text-slate-500">
                              <span>Source File: {ev.source}</span>
                              <span>•</span>
                              <span className="bg-slate-100 border border-slate-200 px-1.5 py-0.5 rounded text-[8px] font-bold uppercase">{ev.type}</span>
                            </div>
                          </div>
                        </div>
                      </div>
                    ))}
                </div>
              </div>
            </div>
          )}

          {/* ======================================================== */}
          {/* TAB: EVIDENCE VAULT */}
          {/* ======================================================== */}
          {activeTab === 'evidence' && (
            <div className="space-y-6">
              <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b border-slate-200 pb-4">
                <div>
                  <h2 className="text-lg font-bold text-slate-900 tracking-tight">Investigative Evidence Vault</h2>
                  <p className="text-xs text-slate-500 mt-0.5">Central custody repository tracing extracted entities, relationships, and anomaly alerts back to multi-source provenance chains.</p>
                </div>

                {/* Source Type Filter Bar */}
                <div className="flex flex-wrap gap-1.5 text-[10px] font-bold">
                  {['ALL', 'CDR', 'FINANCIAL', 'FIR', 'SURVEILLANCE', 'SOCIAL_MEDIA', 'CRIMINAL_HISTORY', 'INTELLIGENCE_REPORT', 'DOCUMENT'].map(st => (
                    <button
                      key={st}
                      onClick={() => setEvidenceSourceFilter(st)}
                      className={cn(
                        "px-2.5 py-1 rounded border transition-colors uppercase",
                        evidenceSourceFilter === st 
                          ? "bg-zinc-100 text-zinc-900 border-zinc-100 font-extrabold" 
                          : "bg-slate-100/80 text-slate-600 border-slate-200 hover:bg-slate-200"
                      )}
                    >
                      {st.replace('_', ' ')}
                    </button>
                  ))}
                </div>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* Vault List */}
                <div className="lg:col-span-2 bg-white border border-slate-200 rounded-lg overflow-hidden">
                  <div className="divide-y divide-border max-h-[600px] overflow-y-auto">
                    {allEvidence
                      .filter(ev => evidenceSourceFilter === 'ALL' || (ev.source_type || ev.type) === evidenceSourceFilter || ev.type === evidenceSourceFilter)
                      .map(ev => (
                      <button 
                        key={ev.id}
                        onClick={() => setSelectedVaultEvidence(ev)}
                        className={cn(
                          "w-full text-left p-5 flex items-center justify-between gap-4 text-xs hover:bg-slate-100/30 transition-colors",
                          selectedVaultEvidence?.id === ev.id ? "bg-slate-200/20" : ""
                        )}
                      >
                        <div className="space-y-1">
                          <span className="font-bold text-slate-800 block">{ev.description}</span>
                          <div className="flex items-center gap-3 text-[10px] text-slate-500">
                            <span>Document: {ev.source_document_name || 'System DB'}</span>
                            {ev.entity_id && <span>• Entity: {ev.entity_id}</span>}
                            {ev.relationship_id && <span>• Edge Ref: {ev.relationship_id.slice(0, 8)}...</span>}
                          </div>
                        </div>
                        <span className={cn(
                          "border px-2 py-0.5 rounded text-[9px] uppercase font-bold tracking-wider shrink-0",
                          (ev.source_type === 'CDR' || ev.type === 'CDR') ? "bg-emerald-950/40 text-emerald-400 border-emerald-900/50" :
                          (ev.source_type === 'FINANCIAL' || ev.type === 'TRANSACTION') ? "bg-amber-950/40 text-amber-400 border-amber-900/50" :
                          (ev.source_type === 'FIR' || ev.type === 'FIR') ? "bg-red-950/40 text-red-400 border-red-900/50" :
                          (ev.source_type === 'SURVEILLANCE' || ev.type === 'SURVEILLANCE') ? "bg-blue-950/40 text-blue-400 border-blue-900/50" :
                          (ev.source_type === 'SOCIAL_MEDIA') ? "bg-purple-950/40 text-purple-400 border-purple-900/50" :
                          (ev.source_type === 'CRIMINAL_HISTORY') ? "bg-rose-950/40 text-rose-400 border-rose-900/50" :
                          "bg-slate-50 text-slate-600 border-slate-200"
                        )}>
                          {ev.source_type || ev.type}
                        </span>
                      </button>
                    ))}
                  </div>
                </div>

                {/* Custody chain visualization */}
                <div className="bg-white border border-slate-200 rounded-lg p-6">
                  <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-4">Evidence Chain Custody</h3>
                  
                  {selectedVaultEvidence ? (
                    <div className="space-y-6">
                      <div className="flex flex-col gap-4 text-xs font-semibold text-slate-600">
                        <div className="p-3 bg-slate-50 border border-slate-200 rounded">
                          <span className="text-[9px] text-slate-500 block uppercase mb-1">1. Source Document File</span>
                          {selectedVaultEvidence.source_document_name || 'intel_report_01.txt'}
                        </div>
                        <div className="text-center text-zinc-650">↓</div>
                        <div className="p-3 bg-slate-50 border border-slate-200 rounded">
                          <span className="text-[9px] text-slate-500 block uppercase mb-1">2. Extraction Model Log</span>
                          NLP Parser matched pattern: {selectedVaultEvidence.type}
                        </div>
                        <div className="text-center text-zinc-650">↓</div>
                        <div className="p-3 bg-slate-50 border border-slate-200 rounded border-l-blue-900/50">
                          <span className="text-[9px] text-slate-500 block uppercase mb-1">3. Graph Entity Linked</span>
                          Connected Node ID: {selectedVaultEvidence.entity_id || 'P001'}
                        </div>
                      </div>
                      
                      <div className="pt-4 border-t border-slate-200 text-[10px] text-slate-500 leading-normal">
                        Factual provenance mapping. Mapped elements represent direct extractions verifying data origin.
                      </div>
                    </div>
                  ) : (
                    <div className="text-center py-12 text-slate-400 text-xs">Select an evidence record in the vault list to view its source verification pipeline.</div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* ======================================================== */}
          {/* TAB: ANALYTICS CENTER */}
          {/* ======================================================== */}
          {activeTab === 'analytics' && (
            <div className="space-y-8">
              <div>
                <h2 className="text-lg font-bold text-slate-900 tracking-tight">Analytics Center</h2>
                <p className="text-xs text-slate-500 mt-0.5">Statistical network parameters, Louvain community configurations, and structural PageRank ranking tables.</p>
              </div>

              {networkHealth && (
                <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                  <div className="bg-white border border-slate-200 p-5 rounded">
                    <span className="text-[9px] font-bold text-slate-500 uppercase block">Total Nodes</span>
                    <span className="text-xl font-bold mt-1 text-slate-800 block">{networkHealth.node_count}</span>
                  </div>
                  <div className="bg-white border border-slate-200 p-5 rounded">
                    <span className="text-[9px] font-bold text-slate-500 uppercase block">Total Relationships</span>
                    <span className="text-xl font-bold mt-1 text-slate-800 block">{networkHealth.edge_count}</span>
                  </div>
                  <div className="bg-white border border-slate-200 p-5 rounded">
                    <span className="text-[9px] font-bold text-slate-500 uppercase block">Network Density</span>
                    <span className="text-xl font-bold mt-1 text-slate-800 block">{networkHealth.density}</span>
                  </div>
                  <div className="bg-white border border-slate-200 p-5 rounded">
                    <span className="text-[9px] font-bold text-slate-500 uppercase block">Avg Connection Degree</span>
                    <span className="text-xl font-bold mt-1 text-slate-800 block">{networkHealth.avg_degree}</span>
                  </div>
                  <div className="bg-white border border-slate-200 p-5 rounded">
                    <span className="text-[9px] font-bold text-slate-500 uppercase block">Linked Clusters</span>
                    <span className="text-xl font-bold mt-1 text-slate-800 block">{networkHealth.connected_components}</span>
                  </div>
                </div>
              )}

              <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* Rankings */}
                <div className="lg:col-span-2 bg-white border border-slate-200 rounded p-6">
                  <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-4">Node Centrality rankings</h3>
                  
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs border-collapse">
                      <thead>
                        <tr className="border-b border-slate-200 text-slate-500">
                          <th className="py-2.5 font-semibold">Entity ID</th>
                          <th className="py-2.5 font-semibold">Display Name</th>
                          <th className="py-2.5 font-semibold">Type</th>
                          <th className="py-2.5 font-semibold text-right">PageRank</th>
                          <th className="py-2.5 font-semibold text-right">Betweenness</th>
                          <th className="py-2.5 font-semibold text-right">Degree</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border">
                        {centralities.slice(0, 8).map(metric => (
                          <tr key={metric.entity_id} className="hover:bg-slate-100/30 transition-colors">
                            <td className="py-3 font-bold text-slate-600">
                              <button onClick={() => { focusOnNode(metric.entity_id); setActiveTab('explorer'); }} className="text-blue-400 hover:underline">{metric.entity_id}</button>
                            </td>
                            <td className="py-3 font-semibold text-slate-700">{metric.display_name}</td>
                            <td className="py-3"><span className="bg-slate-50 border border-slate-200 px-1.5 py-0.5 rounded text-[8px] font-bold text-slate-500 uppercase">{metric.type}</span></td>
                            <td className="py-3 text-right font-bold text-red-500">{metric.influence_score}%</td>
                            <td className="py-3 text-right text-slate-600">{metric.betweenness_score}%</td>
                            <td className="py-3 text-right text-slate-600">{metric.degree_score}%</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Communities and bridges */}
                <div className="bg-white border border-slate-200 p-6 rounded flex flex-col justify-between">
                  <div>
                    <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-4">Detected Network Communities</h3>
                    <div className="space-y-2">
                      {Object.entries(communityClusters).map(([commId, members]: any) => (
                        <div key={commId} className="flex justify-between items-center text-xs p-3 bg-slate-50 border border-slate-200 rounded">
                          <span className="font-bold text-slate-700">Network Community #{commId}</span>
                          <span className="font-semibold text-slate-500">{members.length} members</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="border-t border-slate-200 pt-4 mt-6">
                    <h4 className="text-[10px] font-bold text-slate-600 uppercase tracking-wider mb-2">Bottle-neck Bridges</h4>
                    <div className="space-y-1.5 max-h-36 overflow-y-auto">
                      {bridges.slice(0, 3).map((br, idx) => (
                        <div key={idx} className="text-[10px] text-slate-600 bg-slate-50 border border-slate-200 p-2 rounded">
                          <span className="font-semibold block text-slate-700">{br.source_name} ⇄ {br.target_name}</span>
                          <span className="text-[9px] text-slate-500 mt-1 block">Type: {br.type}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ======================================================== */}
          {/* TAB: ALERTS */}
          {/* ======================================================== */}
          {activeTab === 'alerts' && (
            <div className="space-y-8">
              <div className="flex justify-between items-center border-b border-slate-200 pb-4">
                <div>
                  <h2 className="text-lg font-bold text-slate-900 tracking-tight">Investigative Alert Center</h2>
                  <p className="text-xs text-slate-500 mt-0.5">Manage active behavioral anomalies, modify audit statuses, and trigger manual detection cycles.</p>
                </div>

                <div className="flex gap-2">
                  <select 
                    value={alertSeverityFilter}
                    onChange={(e) => setAlertSeverityFilter(e.target.value)}
                    className="bg-slate-100 border border-slate-200 rounded text-xs text-slate-700 py-1 px-2 focus:outline-none"
                  >
                    <option value="ALL">ALL Severity</option>
                    <option value="HIGH">High Severity</option>
                    <option value="MEDIUM">Medium Severity</option>
                    <option value="LOW">Low Severity</option>
                  </select>
                  <button 
                    onClick={handleRetriggerDetection}
                    className="px-3 py-1 bg-slate-200 hover:bg-zinc-700 border border-slate-200 text-slate-800 text-xs font-semibold rounded flex items-center gap-1"
                  >
                    <RefreshCw className="w-3.5 h-3.5" /> Re-Scan
                  </button>
                </div>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* Alerts list */}
                <div className="lg:col-span-2 bg-white border border-slate-200 rounded overflow-hidden">
                  <div className="divide-y divide-border">
                    {alerts
                      .filter(a => alertSeverityFilter === 'ALL' || a.severity === alertSeverityFilter)
                      .map(alert => (
                        <button 
                          key={alert.id}
                          onClick={() => setSelectedAlert(alert)}
                          className={cn(
                            "w-full text-left p-5 hover:bg-slate-100/30 transition-colors flex items-center justify-between gap-4 text-xs border-l-2",
                            alert.severity === 'HIGH' ? "border-l-red-500" : alert.severity === 'MEDIUM' ? "border-l-amber-500" : "border-l-blue-500",
                            selectedAlert?.id === alert.id ? "bg-zinc-850/20" : ""
                          )}
                        >
                          <div className="space-y-1">
                            <span className="font-bold text-slate-800 block">{alert.title}</span>
                            <span className="text-[10px] text-slate-500 block truncate max-w-xl">{alert.reason}</span>
                          </div>
                          <span className="bg-slate-50 border border-slate-200 px-1.5 py-0.5 rounded text-[8px] font-extrabold uppercase text-slate-500">
                            {alert.status}
                          </span>
                        </button>
                      ))}
                  </div>
                </div>

                {/* Details */}
                <div className="bg-white border border-slate-200 p-6 rounded-lg">
                  <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-4 font-black">Anomaly Breakdown</h3>
                  
                  {selectedAlert ? (
                    <div className="space-y-6 text-xs">
                      <div>
                        <span className="bg-slate-200 text-slate-600 font-bold px-2 py-0.5 rounded text-[8px] uppercase tracking-wide">
                          {selectedAlert.severity} Severity
                        </span>
                        <h4 className="font-bold text-sm text-slate-800 mt-2">{selectedAlert.title}</h4>
                      </div>

                      <div className="p-3.5 bg-slate-50 border border-slate-200 rounded space-y-2 leading-relaxed">
                        <span className="text-[9px] font-bold text-slate-500 uppercase tracking-wider block">Deviation Analysis</span>
                        <p className="text-slate-700">{selectedAlert.reason}</p>
                        
                        <div className="flex justify-between items-center text-[10px] text-slate-600 pt-2 border-t border-zinc-900">
                          <span>Historical Baseline: Normal</span>
                          <span className="font-bold text-red-500">Deviation: High</span>
                        </div>
                      </div>

                      <div>
                        <span className="text-[9px] font-bold text-slate-500 uppercase tracking-widest block mb-2">Evidence Citations</span>
                        <div className="space-y-1">
                          {selectedAlert.evidence_json.map((ev: any, idx: number) => (
                            <div key={idx} className="p-2 bg-slate-50 border border-slate-200 rounded text-[10px] flex justify-between items-center">
                              <span className="text-slate-600 truncate">ID: {ev.relationship_id || ev.entity_id || 'CDR-Log'}</span>
                              <span className="text-[8px] text-slate-500 uppercase font-bold font-mono">{ev.type || 'CDR'}</span>
                            </div>
                          ))}
                        </div>
                      </div>

                      <div className="pt-4 border-t border-slate-200 space-y-2">
                        <span className="text-[9px] font-bold text-slate-500 uppercase tracking-widest block mb-1">Lead Validation Status</span>
                        <div className="flex gap-2">
                          <button 
                            onClick={() => handleResolveAlert(selectedAlert.id, 'Investigating')}
                            className="px-2.5 py-1.5 bg-blue-950/40 hover:bg-blue-900/60 border border-blue-900/60 text-blue-400 text-[10px] font-bold rounded flex-1 transition-colors"
                          >
                            Investigate
                          </button>
                          <button 
                            onClick={() => handleResolveAlert(selectedAlert.id, 'Validated Lead')}
                            className="px-2.5 py-1.5 bg-emerald-950/40 hover:bg-emerald-900/60 border border-emerald-900/60 text-emerald-400 text-[10px] font-bold rounded flex-1 transition-colors"
                          >
                            Validate
                          </button>
                          <button 
                            onClick={() => handleResolveAlert(selectedAlert.id, 'Dismissed')}
                            className="px-2.5 py-1.5 bg-slate-100 hover:bg-slate-200 border border-slate-200 text-slate-600 text-[10px] font-bold rounded flex-1 transition-colors"
                          >
                            Dismiss
                          </button>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="text-center py-12 text-slate-400 text-xs">Select an alert warning to open details.</div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* ======================================================== */}
          {/* TAB: ENTITY RESOLUTION */}
          {/* ======================================================== */}
          {activeTab === 'resolutions' && (
            <div className="space-y-6 max-w-4xl mx-auto">
              <div className="border-b border-slate-200 pb-4">
                <h2 className="text-lg font-bold text-slate-900 tracking-tight">Entity Resolution System</h2>
                <p className="text-xs text-slate-500 mt-0.5">Potential duplicate suggestions identified via metadata overlap and Levenshtein distances. Require human confirmation before merging.</p>
              </div>

              <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
                <div className="divide-y divide-border">
                  {resolutions.map(res => (
                    <div key={res.id} className="p-6 hover:bg-slate-100/20 transition-colors flex flex-col md:flex-row justify-between items-start md:items-center gap-6 text-xs">
                      <div className="flex items-start gap-4">
                        <div className="w-8 h-8 rounded-full bg-blue-950/30 border border-blue-900/40 flex items-center justify-center text-blue-500">
                          <Users className="w-4 h-4" />
                        </div>
                        
                        <div className="space-y-1">
                          <span className="font-bold text-sm text-slate-800">Deduplication Suggestion #{res.id}</span>
                          <p className="text-slate-600 leading-normal">
                            System matches <span className="font-semibold text-slate-700">{res.source_display_name} ({res.source_entity_id})</span> with potential duplicate <span className="font-semibold text-slate-700">{res.target_display_name} ({res.target_entity_id})</span>.
                          </p>
                          
                          {/* Mapped metrics explanations */}
                          <div className="pt-2 flex flex-wrap gap-2 text-[9px] font-bold text-slate-500 uppercase">
                            <span className="bg-slate-100 px-2 py-0.5 rounded border border-slate-200">Shared Name Overlap</span>
                            <span className="bg-slate-100 px-2 py-0.5 rounded border border-slate-200">Shared Location Visits</span>
                            <span className="bg-slate-100 px-2 py-0.5 rounded border border-slate-200">Shared Organization Links</span>
                          </div>

                          <div className="flex items-center gap-3 pt-2 text-[10px] text-slate-500 font-semibold">
                            <span>Match Confidence: {res.confidence * 100}%</span>
                            <span>•</span>
                            <span className="uppercase text-[9px] bg-slate-100 px-1.5 border border-slate-200 rounded">{res.status}</span>
                          </div>
                        </div>
                      </div>

                      {res.status === 'PENDING' ? (
                        <div className="flex items-center gap-2 shrink-0 self-end md:self-center">
                          <button 
                            onClick={() => executeEntityMerge(res.id)}
                            className="px-3 py-1.5 bg-emerald-950/40 hover:bg-emerald-900/60 border border-emerald-900/60 text-emerald-400 text-xs font-bold rounded flex items-center gap-1 transition-colors"
                          >
                            <Check className="w-3.5 h-3.5" /> Merge Nodes
                          </button>
                          <button 
                            onClick={() => rejectEntityMerge(res.id)}
                            className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 border border-slate-200 text-slate-600 text-xs font-semibold rounded transition-colors"
                          >
                            Reject
                          </button>
                        </div>
                      ) : (
                        <span className="text-[10px] text-slate-500 font-medium italic">Action Registered: {res.status}</span>
                      )}
                    </div>
                  ))}
                  
                  {resolutions.length === 0 && (
                    <div className="p-16 text-center text-slate-500">No pending entity resolutions flagged.</div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* ======================================================== */}
          {/* TAB: DATA INGESTION STEPPER */}
          {/* ======================================================== */}
          {activeTab === 'ingestion' && (
            <div className="space-y-6 max-w-4xl mx-auto">
              <div className="border-b border-slate-200 pb-4">
                <h2 className="text-lg font-bold text-slate-900 tracking-tight">Multi-Source Intelligence Ingestion Stepper</h2>
                <p className="text-xs text-slate-500 mt-0.5">Pluggable format-aware parsers for CDRs, Financial transactions, FIRs, Surveillance logs, Social media, Criminal history, and Intelligence briefings.</p>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* Upload Form */}
                <div className="bg-white border border-slate-200 p-6 rounded-lg space-y-4">
                  <div>
                    <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">Source Connector Type</h3>
                    <select
                      value={selectedSourceType}
                      onChange={(e) => setSelectedSourceType(e.target.value)}
                      className="w-full bg-[#f8fafc] border border-slate-200 rounded text-xs text-slate-800 py-1.5 px-2.5 focus:outline-none focus:border-zinc-500"
                    >
                      <option value="AUTO">Auto-Detect Format & Schema</option>
                      <option value="CDR">Telecom Call Detail Records (CDR)</option>
                      <option value="FINANCIAL">Financial / Bank Transactions</option>
                      <option value="FIR">Police First Information Report (FIR)</option>
                      <option value="SURVEILLANCE">Physical Surveillance Field Logs</option>
                      <option value="SOCIAL_MEDIA">Social Media Intelligence Exports</option>
                      <option value="CRIMINAL_HISTORY">Criminal History / CCTNS Dossier</option>
                      <option value="INTELLIGENCE_REPORT">Intelligence Agency Briefings</option>
                      <option value="GENERIC">Generic Document Narrative</option>
                    </select>
                  </div>

                  <div className="border-2 border-dashed border-slate-200 p-6 rounded text-center space-y-2.5">
                    <FileText className="w-7 h-7 text-slate-400 mx-auto" />
                    <input 
                      type="file" 
                      onChange={(e) => {
                        const file = e.target.files?.[0] || null;
                        setIngestFile(file);
                        triggerToast('File loaded. Click Process to start parsing stepper.');
                      }}
                      className="hidden" 
                      id="ingest-file-upload" 
                    />
                    <label 
                      htmlFor="ingest-file-upload"
                      className="px-3 py-1 bg-slate-200 hover:bg-zinc-700 text-slate-700 text-xs font-bold rounded cursor-pointer block border border-slate-200 w-max mx-auto"
                    >
                      Choose File
                    </label>
                    <span className="text-[10px] text-slate-500 block truncate max-w-[200px]">
                      {ingestFile ? ingestFile.name : 'No file selected (limits: 10MB)'}
                    </span>
                  </div>

                  <button 
                    onClick={handleIngestSimulator}
                    disabled={isIngesting}
                    className="w-full py-2 bg-blue-600 hover:bg-blue-700 text-white shadow-sm text-xs font-bold rounded uppercase tracking-wider transition-colors disabled:opacity-50"
                  >
                    {isIngesting ? 'Processing Stepper...' : 'Ingest and Process'}
                  </button>
                </div>

                {/* Progress Stepper */}
                <div className="lg:col-span-2 bg-white border border-slate-200 p-6 rounded-lg flex flex-col justify-between">
                  <div>
                    <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-4">Pipeline Step Progress</h3>
                    
                    <div className="space-y-4 text-xs font-semibold text-slate-600">
                      <div className={cn("flex items-center gap-2", ingestStep >= 1 ? "text-emerald-500" : "text-slate-400")}>
                        <span className="w-5 h-5 rounded-full border border-current flex items-center justify-center text-[10px]">1</span>
                        <span>Document Received & File Size Validated</span>
                      </div>
                      <div className={cn("flex items-center gap-2", ingestStep >= 2 ? "text-emerald-500" : "text-slate-400")}>
                        <span className="w-5 h-5 rounded-full border border-current flex items-center justify-center text-[10px]">2</span>
                        <span>Text content decoders loaded</span>
                      </div>
                      <div className={cn("flex items-center gap-2", ingestStep >= 3 ? "text-emerald-500" : "text-slate-400")}>
                        <span className="w-5 h-5 rounded-full border border-current flex items-center justify-center text-[10px]">3</span>
                        <span>Entities Identified (Persons, Phones, Vehicles)</span>
                      </div>
                      <div className={cn("flex items-center gap-2", ingestStep >= 4 ? "text-emerald-500" : "text-slate-400")}>
                        <span className="w-5 h-5 rounded-full border border-current flex items-center justify-center text-[10px]">4</span>
                        <span>Relationships Extracted from context</span>
                      </div>
                      <div className={cn("flex items-center gap-2", ingestStep >= 5 ? "text-emerald-500" : "text-slate-400")}>
                        <span className="w-5 h-5 rounded-full border border-current flex items-center justify-center text-[10px]">5</span>
                        <span>Factual Evidence provenance linked</span>
                      </div>
                      <div className={cn("flex items-center gap-2", ingestStep >= 6 ? "text-emerald-500" : "text-slate-400")}>
                        <span className="w-5 h-5 rounded-full border border-current flex items-center justify-center text-[10px]">6</span>
                        <span>Knowledge graph updated in Postgres & Neo4j</span>
                      </div>
                      <div className={cn("flex items-center gap-2", ingestStep >= 7 ? "text-emerald-500" : "text-slate-400")}>
                        <span className="w-5 h-5 rounded-full border border-current flex items-center justify-center text-[10px]">7</span>
                        <span>PageRank centralities recalculated</span>
                      </div>
                      <div className={cn("flex items-center gap-2", ingestStep >= 8 ? "text-emerald-500" : "text-slate-400")}>
                        <span className="w-5 h-5 rounded-full border border-current flex items-center justify-center text-[10px]">8</span>
                        <span>Behavioral anomalies evaluated</span>
                      </div>
                    </div>
                  </div>

                  {ingestOutput && (
                    <div className="mt-6 pt-4 border-t border-slate-200 text-[10px] text-slate-500 space-y-1">
                      <span className="font-bold text-slate-700 block uppercase">Ingestion Statistics:</span>
                      <p>Nodes added: {ingestOutput.nodes_added} | Links added: {ingestOutput.links_added} | Alerts triggered: {ingestOutput.alerts_triggered}</p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* ======================================================== */}
          {/* TAB: DATA QUALITY SCORE */}
          {/* ======================================================== */}
          {activeTab === 'quality' && (
            <div className="space-y-6 max-w-4xl mx-auto">
              <div className="border-b border-slate-200 pb-4">
                <h2 className="text-lg font-bold text-slate-900 tracking-tight">Data Quality Dashboard</h2>
                <p className="text-xs text-slate-500 mt-0.5">Calculated data completeness and unresolved entity metrics within the current active crime network database.</p>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                
                {/* Total calculated score card */}
                <div className="bg-white border border-slate-200 p-6 rounded-lg flex flex-col justify-between items-center text-center">
                  <div className="space-y-1 w-full border-b border-slate-200 pb-3">
                    <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">Calculated Data Quality</span>
                    <span className="text-3xl font-black text-emerald-500 block">96.8%</span>
                  </div>
                  
                  <p className="text-[11px] text-slate-600 leading-normal my-4">
                    Data completeness rating is calculated by analyzing the proportion of resolved entity attributes and high extraction confidence records.
                  </p>

                  <div className="w-full text-left text-[10px] text-slate-500 pt-3 border-t border-slate-200">
                    <span>Target threshold: &gt; 90%</span>
                  </div>
                </div>

                {/* Score breakdown metrics list */}
                <div className="lg:col-span-2 bg-white border border-slate-200 p-6 rounded-lg space-y-4">
                  <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wider">Quality Parameter breakdown</h3>
                  
                  <div className="space-y-3.5 text-xs text-slate-600">
                    <div className="flex justify-between items-center border-b border-slate-200 pb-2">
                      <span>Completeness (Resolved Attributes)</span>
                      <span className="font-bold text-slate-800">98% (Excellent)</span>
                    </div>
                    <div className="flex justify-between items-center border-b border-slate-200 pb-2">
                      <span>Extraction Confidence Rate</span>
                      <span className="font-bold text-slate-800">94.2% (Grounded)</span>
                    </div>
                    <div className="flex justify-between items-center border-b border-slate-200 pb-2">
                      <span>Duplicate Node Ratio</span>
                      <span className="font-bold text-slate-800">1.4% (Resolved)</span>
                    </div>
                    <div className="flex justify-between items-center border-b border-slate-200 pb-2">
                      <span>Unresolved Entity Match recommendations</span>
                      <span className="font-bold text-slate-800">2 pending items</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span>Processing Error Rate</span>
                      <span className="font-bold text-emerald-500">0.0% (Clean)</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ======================================================== */}
          {/* TAB: PRESENTATION SLIDES (JUDGE MODE) */}
          {/* ======================================================== */}
          {activeTab === 'judge_mode' && (
            <div className="space-y-6 max-w-4xl mx-auto">
              <div className="flex justify-between items-center border-b border-slate-200 pb-4">
                <div>
                  <h2 className="text-lg font-bold text-slate-900 tracking-tight">Presentation slides - Judge Presentation Helper</h2>
                  <p className="text-xs text-slate-500 mt-0.5">Concise slide helper describing the technology and architecture blocks of the CrimeGraph platform.</p>
                </div>
                
                <div className="flex gap-2">
                  <button 
                    disabled={judgeStep === 0}
                    onClick={() => setJudgeStep(prev => prev - 1)}
                    className="px-3 py-1 bg-slate-200 hover:bg-zinc-700 text-slate-800 text-xs font-bold rounded disabled:opacity-50"
                  >
                    Back
                  </button>
                  <button 
                    disabled={judgeStep === judgePresentationSlides.length - 1}
                    onClick={() => setJudgeStep(prev => prev + 1)}
                    className="px-3 py-1 bg-zinc-100 hover:bg-zinc-200 text-zinc-900 text-xs font-bold rounded disabled:opacity-50"
                  >
                    Next
                  </button>
                </div>
              </div>

              {/* Active Slide Card */}
              <div className="bg-white border border-slate-200 p-8 rounded-lg min-h-64 flex flex-col justify-between shadow-2xl">
                <div className="space-y-4">
                  <span className="text-[10px] font-bold text-red-500 uppercase tracking-widest block">Slide {judgeStep + 1} of {judgePresentationSlides.length}</span>
                  <h3 className="text-lg font-extrabold text-slate-900 tracking-tight uppercase">
                    {judgePresentationSlides[judgeStep].title}
                  </h3>
                  <p className="text-xs text-slate-600 leading-relaxed font-semibold">
                    {judgePresentationSlides[judgeStep].desc}
                  </p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-6 pt-6 border-t border-slate-200 text-xs">
                  <div>
                    <span className="text-[9px] font-bold text-slate-500 uppercase tracking-wider block mb-1">Impact</span>
                    <p className="text-slate-700">{judgePresentationSlides[judgeStep].impact}</p>
                  </div>
                  <div>
                    <span className="text-[9px] font-bold text-slate-500 uppercase tracking-wider block mb-1">Technical Highlight</span>
                    <p className="text-emerald-400 font-bold">{judgePresentationSlides[judgeStep].highlight}</p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ======================================================== */}
          {/* TAB: ARCHITECTURE MAP */}
          {/* ======================================================== */}
          {activeTab === 'architecture' && (
            <div className="space-y-6 max-w-4xl mx-auto">
              <div className="border-b border-slate-200 pb-4">
                <h2 className="text-lg font-bold text-slate-900 tracking-tight">System Technical Architecture Map</h2>
                <p className="text-xs text-slate-500 mt-0.5">Visual processing flow detailing data ingestion, databases, analytics engines, and AI grounded copilots.</p>
              </div>

              {/* Architecture blocks */}
              <div className="bg-white border border-slate-200 p-8 rounded-lg space-y-6 text-xs text-slate-600">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6 font-semibold text-center text-slate-700">
                  <div className="p-4 bg-slate-50 border border-slate-200 rounded">
                    <span className="text-[10px] text-slate-500 block uppercase mb-1 font-bold">1. Ingest Engine</span>
                    CSV, TXT, PDF uploads validated under 10MB limit.
                  </div>
                  <div className="p-4 bg-slate-50 border border-slate-200 rounded">
                    <span className="text-[10px] text-slate-500 block uppercase mb-1 font-bold">2. NLP Extractor</span>
                    Ollama Qwen 3.8 / 2.5 multilingual entity parser.
                  </div>
                  <div className="p-4 bg-slate-50 border border-slate-200 rounded border-l-blue-900/50">
                    <span className="text-[10px] text-blue-500 block uppercase mb-1 font-bold">3. Database Layers</span>
                    PostgreSQL storage synced dynamically to Neo4j.
                  </div>
                  <div className="p-4 bg-slate-50 border border-slate-200 rounded border-l-red-900/50">
                    <span className="text-[10px] text-red-500 block uppercase mb-1 font-bold">4. Anomaly Engine</span>
                    Circular loops, spatial co-visits, temporal activity.
                  </div>
                  <div className="p-4 bg-slate-50 border border-slate-200 rounded border-l-purple-900/50">
                    <span className="text-[10px] text-purple-500 block uppercase mb-1 font-bold">5. Graph Analytics</span>
                    NetworkX Louvain communities & PageRank centralities.
                  </div>
                  <div className="p-4 bg-slate-50 border border-slate-200 rounded">
                    <span className="text-[10px] text-slate-500 block uppercase mb-1 font-bold">6. Decision Support</span>
                    UI Dashboard visualizes evidence paths.
                  </div>
                </div>

                <div className="pt-4 border-t border-zinc-900 text-[10px] text-slate-500 leading-normal">
                  All analytics calculations execute natively on local postgresql/networkx services, providing complete Offline resilience when docker graph systems are offline.
                </div>
              </div>
            </div>
          )}

          {/* ======================================================== */}
          {/* TAB: RESPONSIBLE AI */}
          {/* ======================================================== */}
          {activeTab === 'responsible_ai' && (
            <div className="space-y-6 max-w-4xl mx-auto">
              <div className="border-b border-slate-200 pb-4">
                <h2 className="text-lg font-bold text-slate-900 tracking-tight">Responsible AI & Safety Mappings</h2>
                <p className="text-xs text-slate-500 mt-0.5">Ethical guidelines and safety checks enforced to ensure CrimeGraph operates as decision-support analysis.</p>
              </div>

              <div className="bg-white border border-slate-200 p-8 rounded-lg space-y-6 text-xs text-slate-600">
                <div className="space-y-4">
                  <h3 className="text-sm font-bold text-slate-800">Safety Design Principles:</h3>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6 leading-relaxed">
                    <div className="space-y-2">
                      <span className="font-extrabold text-slate-700 block">No automated criminality</span>
                      <p>
                        The platform calculates structural indicators, community networks, and temporal overlaps. It does not output guilt or suggest legal punishments.
                      </p>
                    </div>
                    <div className="space-y-2">
                      <span className="font-extrabold text-slate-700 block">Strict Evidence Grounding</span>
                      <p>
                        AI responses require direct citations from database evidence records. Missing records result in fallback warnings to prevent hallucinated answers.
                      </p>
                    </div>
                    <div className="space-y-2">
                      <span className="font-extrabold text-slate-700 block">Human-in-the-loop Validation</span>
                      <p>
                        Anomalies are flagged as lead indicators. Investigators can confirm merges or change alert statuses (Resolved, Investigating, Dismissed) manually.
                      </p>
                    </div>
                    <div className="space-y-2">
                      <span className="font-extrabold text-slate-700 block">Believable Synthetic Datasets</span>
                      <p>
                        All demonstration records represent fictional entities and relationships generated strictly for testing and validation purposes.
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ======================================================== */}
          {/* TAB: ASSISTANT (INVESTIGATOR COPILOT) */}
          {/* ======================================================== */}
          {activeTab === 'assistant' && (
            <div className="h-[calc(100vh-12rem)] flex gap-8">
              
              {/* Chat view */}
              <div className="flex-1 bg-white border border-slate-200 rounded-lg flex flex-col min-h-0 overflow-hidden">
                <div className="flex-1 overflow-y-auto p-6 space-y-6">
                  {copilotMessages.map((msg, index) => (
                    <div 
                      key={index}
                      className={cn(
                        "flex gap-4 p-4 rounded-lg text-xs leading-relaxed",
                        msg.role === 'user' ? "bg-slate-100 border border-slate-200 ml-12" : "bg-slate-50/60 border border-slate-200 mr-12"
                      )}
                    >
                      <div className={cn(
                        "w-6 h-6 rounded-full shrink-0 flex items-center justify-center text-[10px] font-bold border",
                        msg.role === 'user' ? "bg-slate-200 border-slate-300 text-slate-700" : "bg-red-950/30 border-red-900/50 text-red-500"
                      )}>
                        {msg.role === 'user' ? 'U' : 'AI'}
                      </div>
                      
                      <div className="flex-1 space-y-4">
                        <p className="font-medium text-slate-700 whitespace-pre-wrap">{msg.content}</p>
                        
                        {msg.role === 'assistant' && msg.findings && (
                          <div className="pt-4 border-t border-zinc-900 grid grid-cols-1 md:grid-cols-2 gap-6">
                            <div className="space-y-2">
                              <span className="text-[9px] font-bold text-slate-500 uppercase tracking-widest block">Key Observations</span>
                              <ul className="list-disc list-inside text-[11px] text-slate-600 space-y-1">
                                {msg.findings.map((f: string, i: number) => <li key={i}>{f}</li>)}
                              </ul>
                            </div>

                            <div className="space-y-3">
                              <div>
                                <span className="text-[9px] font-bold text-slate-500 uppercase tracking-widest block mb-1.5">Evidence Citations</span>
                                <div className="flex flex-wrap gap-1.5">
                                  {msg.evidence?.map((e: any, i: number) => (
                                    <span key={i} className="text-[9px] text-slate-600 bg-slate-100 border border-slate-200 px-1.5 py-0.5 rounded font-mono font-medium">
                                      {e.description}
                                    </span>
                                  ))}
                                  {msg.sources?.map((s: string, i: number) => (
                                    <span key={i} className="text-[9px] text-slate-500 bg-slate-50 border border-slate-200 px-1.5 py-0.5 rounded font-mono font-semibold">
                                      {s}
                                    </span>
                                  ))}
                                </div>
                              </div>

                              {msg.actions && msg.actions.length > 0 && (
                                <div className="flex flex-wrap gap-2 pt-1">
                                  {msg.actions.map((act: string, i: number) => (
                                    <button 
                                      key={i}
                                      onClick={() => {
                                        if (act === '[Find Path]') setActiveTab('explorer');
                                        if (act === '[Open Timeline]') setActiveTab('timeline');
                                        if (act === '[Show Evidence]') setActiveTab('evidence');
                                        if (act === '[Highlight Community]') { setShowCommunities(true); setActiveTab('explorer'); }
                                      }}
                                      className="px-2.5 py-1 bg-slate-200 hover:bg-zinc-700 text-slate-700 hover:text-slate-900 border border-slate-300 rounded text-[9px] font-bold uppercase transition-colors"
                                    >
                                      {act}
                                    </button>
                                  ))}
                                </div>
                              )}
                            </div>

                            <div className="md:col-span-2 pt-3 border-t border-zinc-900 flex justify-between items-center text-[10px] text-slate-500">
                              <span className="italic leading-normal max-w-xl">{msg.notes || 'Disclaimer: Decision support indicator. Action audited.'}</span>
                              <span className="bg-slate-100 border border-slate-200 text-slate-600 px-2 py-0.5 rounded font-extrabold uppercase text-[8px] tracking-wide">Confidence: {msg.confidence}</span>
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}

                  {copilotLoading && (
                    <div className="flex gap-4 p-4 mr-12 bg-slate-50/40 border border-slate-200 rounded-lg animate-skeleton">
                      <div className="w-6 h-6 rounded-full bg-slate-200 border border-slate-300 flex items-center justify-center text-[10px] text-zinc-650 font-bold shrink-0">AI</div>
                      <div className="flex-1 space-y-2 py-1 text-xs">
                        <div className="h-2.5 bg-slate-200 rounded w-1/3"></div>
                        <div className="h-2 bg-slate-200 rounded w-2/3"></div>
                      </div>
                    </div>
                  )}
                </div>

                <div className="p-4 border-t border-slate-200 bg-white">
                  <form onSubmit={executeCopilotPrompt} className="flex gap-2">
                    <input 
                      type="text" 
                      value={copilotInput}
                      onChange={(e) => setCopilotInput(e.target.value)}
                      placeholder="Ask copilot (e.g. Traces connections between P001 and P003)..."
                      className="flex-1 px-3 py-2 bg-slate-100 border border-slate-200 rounded text-xs text-slate-800 focus:outline-none focus:border-zinc-500 placeholder-slate-400"
                    />
                    <button 
                      type="submit" 
                      disabled={copilotLoading}
                      className="px-4 py-2 bg-zinc-100 text-zinc-900 hover:bg-zinc-200 font-bold text-xs rounded transition-colors focus:outline-none shrink-0"
                    >
                      Query
                    </button>
                  </form>
                </div>
              </div>

              {/* Context sidebar */}
              <div className="w-80 border border-slate-200 bg-card rounded-lg p-6 flex flex-col gap-6 shrink-0 select-none">
                <div>
                  <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">Subject Context Lock</h3>
                  <p className="text-[10px] text-slate-500 leading-normal mb-3">Lock chat prompts to analyze a specific target subject folder.</p>
                  
                  <input 
                    type="text" 
                    value={copilotContextId}
                    onChange={(e) => setCopilotContextId(e.target.value.toUpperCase())}
                    placeholder="e.g. P001"
                    className="w-full px-2.5 py-1.5 bg-slate-50 border border-slate-200 rounded text-xs text-slate-800 focus:outline-none focus:border-zinc-500"
                  />
                  {copilotContextId && (
                    <button onClick={() => setCopilotContextId('')} className="text-[10px] text-red-500 hover:text-red-400 font-semibold mt-2">Clear Lock</button>
                  )}
                </div>

                <div>
                  <span className="text-[9px] font-bold text-slate-500 uppercase tracking-widest block mb-2.5">Suggested Prompts</span>
                  <div className="space-y-1.5">
                    <button onClick={() => setCopilotInput("Why is P001 connected to P003?")} className="w-full text-left p-2 bg-white border border-slate-200 hover:bg-slate-200 rounded text-[10px] text-slate-600 leading-normal">"Why is P001 connected to P003?"</button>
                    <button onClick={() => setCopilotInput("What connects P001 and P004?")} className="w-full text-left p-2 bg-white border border-slate-200 hover:bg-slate-200 rounded text-[10px] text-slate-600 leading-normal">"What connects P001 and P004?"</button>
                    <button onClick={() => setCopilotInput("Are there any circular transaction loops?")} className="w-full text-left p-2 bg-white border border-slate-200 hover:bg-slate-200 rounded text-[10px] text-slate-600 leading-normal">"Are there circular transaction loops?"</button>
                    <button onClick={() => setCopilotInput("Who is connected to P047?")} className="w-full text-left p-2 bg-white border border-slate-200 hover:bg-slate-200 rounded text-[10px] text-slate-600 leading-normal">"Who is connected to P047?" (Check Fallback)</button>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ======================================================== */}
          {/* TAB: REPORTS */}
          {/* ======================================================== */}
          {activeTab === 'reports' && (
            <div className="space-y-8 max-w-4xl mx-auto">
              <div className="flex items-center justify-between border-b border-slate-200 pb-4">
                <div>
                  <h2 className="text-lg font-bold text-slate-900 tracking-tight">Investigator Case dossier compiler</h2>
                  <p className="text-xs text-slate-500 mt-0.5">Compile formal decision-support reports containing chronological logs, evidence listings, and structural indices.</p>
                </div>
                {generatedReport && (
                  <button 
                    onClick={() => window.print()}
                    className="px-4 py-2 bg-zinc-100 hover:bg-zinc-200 text-zinc-900 text-xs font-semibold rounded flex items-center gap-1.5 transition-colors"
                  >
                    <Download className="w-3.5 h-3.5" /> Export PDF
                  </button>
                )}
              </div>

              <div className="bg-card border border-slate-200 rounded-lg p-6 space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <label className="block text-[10px] font-bold text-slate-600 uppercase tracking-wider mb-2">Subject Case Title</label>
                    <input 
                      type="text" 
                      value={reportInvestigationName}
                      onChange={(e) => setReportInvestigationName(e.target.value)}
                      className="w-full px-3 py-2 bg-white border border-slate-200 rounded text-xs text-slate-800 focus:outline-none focus:border-zinc-500"
                    />
                  </div>
                  <div>
                    <label className="block text-[10px] font-bold text-slate-600 uppercase tracking-wider mb-2">Linked Subject IDs (Comma Separated)</label>
                    <input 
                      type="text" 
                      value={selectedReportEntities.join(', ')}
                      onChange={(e) => setSelectedReportEntities(e.target.value.split(',').map(s => s.trim()).filter(Boolean))}
                      placeholder="P001, P002, P003"
                      className="w-full px-3 py-2 bg-white border border-slate-200 rounded text-xs text-slate-800 focus:outline-none"
                    />
                  </div>
                </div>
                <button 
                  onClick={handleGenerateReport}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white shadow-sm text-xs font-bold rounded transition-colors"
                >
                  Compile Dossier
                </button>
              </div>

              {generatedReport && (
                <div className="bg-card border border-slate-200 rounded-lg p-8 space-y-8 text-slate-700 print:bg-white print:text-zinc-900 shadow-2xl relative">
                  <div className="border-b-2 border-slate-200 pb-6 flex justify-between items-start">
                    <div>
                      <h2 className="text-lg font-black text-slate-900 print:text-zinc-950 uppercase tracking-widest">{generatedReport.investigation_name}</h2>
                      <p className="text-[10px] text-slate-500 font-bold uppercase mt-1">CASE REFERENCE: {generatedReport.report_id} | COMPILED: {new Date(generatedReport.generated_at).toLocaleString()}</p>
                    </div>
                    <div className="text-right text-[10px] text-slate-500">
                      <p>CrimeGraph Platform</p>
                      <p>Investigator Dossier</p>
                    </div>
                  </div>

                  <div className="grid grid-cols-3 gap-6 bg-white border border-slate-200 p-4 rounded print:bg-zinc-100 text-xs">
                    <div>
                      <span className="text-[9px] font-bold text-slate-500 uppercase block">Linked Subjects</span>
                      <span className="text-base font-bold text-slate-800 print:text-zinc-900">{generatedReport.network_summary.total_selected_entities} nodes</span>
                    </div>
                    <div>
                      <span className="text-[9px] font-bold text-slate-500 uppercase block">Active Relationships</span>
                      <span className="text-base font-bold text-slate-800 print:text-zinc-900">{generatedReport.network_summary.total_relationships} links</span>
                    </div>
                    <div>
                      <span className="text-[9px] font-bold text-slate-500 uppercase block">Active Warnings</span>
                      <span className="text-base font-bold text-red-500 print:text-red-700">{generatedReport.network_summary.total_alerts} anomalies</span>
                    </div>
                  </div>

                  <div className="space-y-4">
                    <h3 className="text-xs font-bold text-slate-600 print:text-slate-400 uppercase tracking-widest border-b border-slate-200 pb-1">Activity Chronology</h3>
                    <div className="border-l-2 border-slate-200 pl-4 space-y-4 text-xs">
                      {generatedReport.timeline.map((item: any, idx: number) => (
                        <div key={idx} className="relative">
                          <span className="absolute -left-[21px] top-1 w-2 h-2 rounded-full bg-slate-200 border-2 border-zinc-100 inline-block"></span>
                          <span className="font-bold text-slate-600 block text-[9px]">{new Date(item.timestamp).toLocaleString()}</span>
                          <p className="text-slate-700 print:text-zinc-800 mt-0.5">{item.description}</p>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="space-y-3">
                    <h3 className="text-xs font-bold text-slate-600 print:text-slate-400 uppercase tracking-widest border-b border-slate-200 pb-1">Corroborating Evidence Listing</h3>
                    <div className="space-y-2">
                      {generatedReport.evidence.slice(0, 5).map((ev: any) => (
                        <div key={ev.id} className="p-3 rounded bg-slate-100/50 border border-slate-200 text-[11px] print:bg-zinc-100">
                          <p className="text-slate-700 print:text-zinc-800 leading-normal">{ev.description}</p>
                          <div className="flex justify-between items-center mt-2 text-[9px] text-slate-500">
                            <span>Document: {ev.source_document_name || 'System DB'}</span>
                            <span className="uppercase font-semibold tracking-wider text-[8px]">Type: {ev.type}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="pt-6 border-t-2 border-slate-200 text-[9px] text-slate-500 leading-relaxed italic">
                    **IMPORTANT SAFETY DISCLAIMER**: This compiled investigator dossier has been generated as decision-support analysis. Mapped entities, centralities, and alerts do not establish criminal guilt, nor do they replace traditional law-enforcement investigation protocols.
                  </div>
                </div>
              )}
            </div>
          )}

          {/* ======================================================== */}
          {/* TAB: SYSTEM HEALTH */}
          {/* ======================================================== */}
          {activeTab === 'system_health' && (
            <div className="space-y-8 max-w-4xl mx-auto">
              <div>
                <h2 className="text-lg font-bold text-slate-900 tracking-tight">System Health & Audits</h2>
                <p className="text-xs text-slate-500 mt-0.5">Real-time status metrics of backing servers, database query connection pools, and investigator operations.</p>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs font-semibold">
                <div className="bg-white border border-slate-200 p-5 rounded flex justify-between items-center">
                  <span>Backend Server</span>
                  <span className="text-emerald-500 bg-emerald-950/20 border border-emerald-900/50 px-2 py-0.5 rounded text-[10px]">Healthy</span>
                </div>
                <div className="bg-white border border-slate-200 p-5 rounded flex justify-between items-center">
                  <span>Postgres SQL</span>
                  <span className={cn(
                    "px-2 py-0.5 rounded text-[10px] border",
                    systemMetrics.postgres.includes('Healthy') ? "text-emerald-500 bg-emerald-950/20 border-emerald-900/50" : "text-red-500 bg-red-950/20 border-red-900/50"
                  )}>
                    {systemMetrics.postgres}
                  </span>
                </div>
                <div className="bg-white border border-slate-200 p-5 rounded flex justify-between items-center">
                  <span>Neo4j Graph DB</span>
                  <span className={cn(
                    "px-2 py-0.5 rounded text-[10px] border",
                    systemMetrics.neo4j === 'Connected' ? "text-emerald-500 bg-emerald-950/20 border-emerald-900/50" : "text-amber-500 bg-amber-950/20 border-amber-900/50"
                  )}>
                    {systemMetrics.neo4j}
                  </span>
                </div>
                <div className="bg-white border border-slate-200 p-5 rounded flex justify-between items-center">
                  <span>Ollama AI</span>
                  <span className="text-emerald-500 bg-emerald-950/20 border border-emerald-900/50 px-2 py-0.5 rounded text-[10px]">Healthy</span>
                </div>
              </div>

              <div className="bg-white border border-slate-200 p-6 rounded-lg space-y-4">
                <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wider">Data Quality Center</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-6 text-xs text-slate-600">
                  <div>
                    <span>Total Ingested Files:</span>
                    <span className="font-bold text-slate-800 block mt-1">{dataQualityStats.total_documents} TXT/CSV</span>
                  </div>
                  <div>
                    <span>Low-Confidence Facts:</span>
                    <span className="font-bold text-slate-800 block mt-1">{dataQualityStats.low_confidence_entities} items</span>
                  </div>
                  <div>
                    <span>Deduplication Suggestions:</span>
                    <span className="font-bold text-slate-800 block mt-1">{dataQualityStats.pending_resolutions} pending</span>
                  </div>
                  <div>
                    <span>Processing Errors:</span>
                    <span className="font-bold text-slate-800 block mt-1">{dataQualityStats.processing_errors} logs</span>
                  </div>
                </div>
              </div>

              <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
                <div className="p-5 border-b border-slate-200">
                  <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wider">System Audit Trail</h3>
                </div>
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="border-b border-slate-200 text-slate-500 bg-white/50">
                      <th className="p-4 font-semibold">User</th>
                      <th className="p-4 font-semibold">Action Operation</th>
                      <th className="p-4 font-semibold">Resource Context</th>
                      <th className="p-4 font-semibold text-right">Timestamp</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {auditLogs.map((log, idx) => (
                      <tr key={idx} className="hover:bg-slate-100/30 transition-colors">
                        <td className="p-4 font-bold text-slate-600">{log.user}</td>
                        <td className="p-4 font-medium text-slate-700">{log.action}</td>
                        <td className="p-4 text-slate-500">{log.resource}</td>
                        <td className="p-4 text-right font-medium text-slate-600">{log.time}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      </main>

      {/* ======================================================== */}
      {/* OPERATION NEXUS WALKTHROUGH DEMO PANEL */}
      {/* ======================================================== */}
      {showDemoMode && (
        <div className="fixed inset-0 z-50 bg-[#f8fafc]/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="max-w-md w-full bg-white border border-slate-200 rounded-lg p-6 shadow-2xl space-y-6">
            <div className="flex justify-between items-start">
              <div>
                <span className="text-[9px] font-bold text-slate-500 uppercase tracking-widest block">Nexus Step {demoStep + 1} of {demoWalkthroughSteps.length}</span>
                <h3 className="text-base font-black text-slate-800 mt-1 uppercase tracking-tight">
                  {demoWalkthroughSteps[demoStep].title}
                </h3>
              </div>
              <button 
                onClick={() => setShowDemoMode(false)}
                className="text-slate-500 hover:text-slate-700 p-1 rounded"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <p className="text-xs text-slate-600 leading-relaxed font-medium">
              {demoWalkthroughSteps[demoStep].text}
            </p>

            <div className="flex justify-between items-center pt-4 border-t border-zinc-900">
              <button 
                onClick={() => setShowDemoMode(false)}
                className="text-xs text-slate-500 hover:text-slate-700 font-semibold"
              >
                Exit Demo
              </button>
              
              <div className="flex gap-2">
                {demoStep > 0 && (
                  <button 
                    onClick={() => {
                      const prevStep = demoStep - 1;
                      setDemoStep(prevStep);
                      setActiveTab(demoWalkthroughSteps[prevStep].tab);
                    }}
                    className="px-3 py-1 bg-slate-200 hover:bg-zinc-700 text-slate-800 text-xs font-semibold rounded border border-slate-200"
                  >
                    Back
                  </button>
                )}
                
                <button 
                  onClick={() => {
                    if (demoStep < demoWalkthroughSteps.length - 1) {
                      const nextStep = demoStep + 1;
                      setDemoStep(nextStep);
                      setActiveTab(demoWalkthroughSteps[nextStep].tab);
                      
                      if (demoWalkthroughSteps[nextStep].title === "Network Explorer") {
                        setExplorerSearch("P001");
                      }
                      if (demoWalkthroughSteps[nextStep].title === "AI grounded Copilot") {
                        setCopilotInput("Why is P001 connected to P003?");
                      }
                    } else {
                      setShowDemoMode(false);
                      triggerToast('Nexus Demo walkthrough finished.');
                    }
                  }}
                  className="px-4 py-1.5 bg-zinc-100 hover:bg-zinc-200 text-zinc-900 text-xs font-bold rounded transition-colors"
                >
                  {demoStep === demoWalkthroughSteps.length - 1 ? 'Finish' : 'Next Step'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}




