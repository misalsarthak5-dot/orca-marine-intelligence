import { ChatMessage, SuggestionChip, AgentInfo, TrendDataPoint } from '@/types';

// ── Trend data for productivity query ───────────────────────
export const trendData: TrendDataPoint[] = [
  { month: 'Jan', sst: 26.2, chlorophyll: 1.8 },
  { month: 'Feb', sst: 26.5, chlorophyll: 1.7 },
  { month: 'Mar', sst: 27.0, chlorophyll: 1.5 },
  { month: 'Apr', sst: 27.8, chlorophyll: 1.3 },
  { month: 'May', sst: 28.4, chlorophyll: 1.1 },
  { month: 'Jun', sst: 28.9, chlorophyll: 0.9 },
  { month: 'Jul', sst: 28.2, chlorophyll: 1.0 },
  { month: 'Aug', sst: 27.6, chlorophyll: 1.2 },
  { month: 'Sep', sst: 28.4, chlorophyll: 1.2 },
];

// ── Suggestion chips ────────────────────────────────────────
export const suggestionChips: SuggestionChip[] = [
  { id: 'chip-1', label: 'ask_suggestion1', query: 'Is it safe to fish tomorrow?' },
  { id: 'chip-2', label: 'ask_suggestion2', query: 'Find nearest PFZ' },
  { id: 'chip-3', label: 'ask_suggestion3', query: 'What areas should I avoid?' },
  { id: 'chip-4', label: 'ask_suggestion4', query: 'Show the safest route' },
  { id: 'chip-5', label: 'ask_suggestion5', query: 'Why has productivity declined?' },
];

// ── Mock conversation responses (English) ───────────────────
export const mockResponses: Record<string, ChatMessage> = {
  safety: {
    id: 'resp-safety',
    role: 'orca',
    content:
      'Overall Sector Risk: LOW (18/100) — CONDITIONS SUITABLE. Pre-dawn and morning window (05:00 - 11:00 IST) offers calm sea conditions ideal for mechanized and motorized fishing craft (>9m). High-yield pelagic activity is pinpointed at PFZ Alpha (32.4 NM WSW) with optimal chlorophyll readings. Artisanal craft may operate until 13:00 IST prior to afternoon swell pick-up.',
    timestamp: '09:43 IST',
    riskLevel: 'low',
    verdictTitle: 'VERDICT: CONDITIONS SUITABLE',
    factors: [
      { id: 'f1', label: 'factor_wind', value: '14 kts (SW)', status: 'Moderate', statusColor: 'green', icon: 'wind' },
      { id: 'f2', label: 'factor_waves', value: '1.8 m (Acceptable)', status: 'Within threshold', statusColor: 'green', icon: 'waves' },
      { id: 'f3', label: 'factor_lightning', value: 'Clear (0%)', status: 'No alert', statusColor: 'green', icon: 'zap' },
      { id: 'f4', label: 'factor_cyclone', value: 'Nil Active', status: 'No depression', statusColor: 'green', icon: 'tornado' },
      { id: 'f5', label: 'factor_geofence', value: 'Clear (>3.5NM)', status: 'No conflict', statusColor: 'green', icon: 'shield' },
    ],
    recommendation:
      'Fishing conditions are currently suitable. Continue monitoring official marine advisories before departure.',
    attachments: [
      { type: 'safety', label: 'View Safety Assessment' },
      { type: 'map', label: 'View Risk Map' },
    ],
  },
  pfz: {
    id: 'resp-pfz',
    role: 'orca',
    content:
      'Nearest PFZ identified: PFZ Alpha, 32 km from current location. SST readings are suitable (28.2°C), chlorophyll concentration is high (1.4 mg/m³), and marine risk is low. This zone currently shows favourable conditions for fishing.',
    timestamp: '09:44 IST',
    pfz: {
      id: 'pfz-alpha',
      name: 'PFZ Alpha',
      coordinates: [18.85, 72.45],
      boundary: [[18.82, 72.40], [18.82, 72.50], [18.88, 72.50], [18.88, 72.40]],
      distance: '32 km',
      sst: '28.2°C',
      sstStatus: 'Suitable',
      chlorophyll: '1.4 mg/m³',
      chlorophyllStatus: 'High',
      marineRisk: 'low',
      probability: 'high',
      recommendation: 'This zone currently shows favourable conditions.',
    },
    attachments: [
      { type: 'pfz', label: 'Send Waypoint to Helm' },
      { type: 'map', label: 'View on Map' },
    ],
  },
  avoidance: {
    id: 'resp-avoidance',
    role: 'orca',
    content: '3 areas identified that should be avoided during the selected period:',
    timestamp: '09:45 IST',
    avoidanceZones: [
      { label: 'High-Wave Zone', reason: 'Elevated wave conditions (2.0–2.4 m) expected 14:00–17:30 IST' },
      { label: 'Lightning Alert Region', reason: 'Convective activity detected, lightning risk until 14:30 IST' },
      { label: 'Restricted / Geofenced Area', reason: 'Naval exercise zone — temporary restricted area' },
    ],
    attachments: [
      { type: 'map', label: 'View Risk Map' },
    ],
  },
  route: {
    id: 'resp-route',
    role: 'orca',
    content:
      'Recommended safe corridor identified. A 2° port deviation from the direct trajectory reduces estimated wave exposure by approximately 40%. Route avoids the high-wave zone and restricted naval exercise area.',
    timestamp: '09:46 IST',
    attachments: [
      { type: 'route', label: 'View Route on Map' },
      { type: 'map', label: 'Review Route' },
    ],
  },
  productivity: {
    id: 'resp-productivity',
    role: 'orca',
    content:
      'Productivity trend analysis for Sector 4: Chlorophyll concentration decreased approximately 50% (1.8 → 0.9 mg/m³) while SST increased by 2.7°C over the Jan–Jun period. This correlational pattern is consistent with thermal stratification reducing nutrient upwelling.',
    timestamp: '09:47 IST',
    trendData: trendData,
    trendNarrative:
      'Correlational observation — not a confirmed causal relationship. Consult regional fisheries authorities for a definitive assessment.',
    attachments: [
      { type: 'chart', label: 'View Trend Chart' },
    ],
  },
};

// ── Mock responses in Hindi ─────────────────────────────────
export const mockResponsesHi: Record<string, ChatMessage> = {
  safety: {
    ...mockResponses.safety,
    id: 'resp-safety-hi',
    content:
      'समग्र सेक्टर जोखिम: कम (18/100) — परिस्थितियाँ उपयुक्त। भोर और सुबह की खिड़की (05:00 - 11:00 IST) यंत्रीकृत और मोटर चालित मछली पकड़ने की नौकाओं (>9m) के लिए शांत समुद्री परिस्थितियाँ प्रदान करती है।',
    recommendation: 'मछली पकड़ने की स्थिति वर्तमान में उपयुक्त है। प्रस्थान से पहले आधिकारिक समुद्री सलाह की निगरानी जारी रखें।',
  },
  pfz: {
    ...mockResponses.pfz,
    id: 'resp-pfz-hi',
    content:
      'निकटतम PFZ पहचाना गया: PFZ अल्फा, वर्तमान स्थान से 32 किमी। SST रीडिंग उपयुक्त (28.2°C), क्लोरोफिल सांद्रता अधिक (1.4 mg/m³), और समुद्री जोखिम कम है।',
  },
  avoidance: {
    ...mockResponses.avoidance,
    id: 'resp-avoidance-hi',
    content: 'चयनित अवधि में 3 क्षेत्रों से बचना चाहिए:',
    avoidanceZones: [
      { label: 'उच्च-तरंग क्षेत्र', reason: 'ऊंची लहरें (2.0–2.4 मीटर) 14:00–17:30 IST' },
      { label: 'बिजली चेतावनी क्षेत्र', reason: 'संवहनी गतिविधि, 14:30 IST तक बिजली का खतरा' },
      { label: 'प्रतिबंधित / जियोफ़ेंस क्षेत्र', reason: 'नौसैनिक अभ्यास क्षेत्र — अस्थायी प्रतिबंधित' },
    ],
  },
  route: {
    ...mockResponses.route,
    id: 'resp-route-hi',
    content: 'अनुशंसित सुरक्षित मार्ग पहचाना गया। सीधे मार्ग से 2° का विचलन लहर जोखिम को लगभग 40% कम करता है।',
  },
  productivity: {
    ...mockResponses.productivity,
    id: 'resp-productivity-hi',
    content: 'सेक्टर 4 के लिए उत्पादकता प्रवृत्ति विश्लेषण: क्लोरोफिल सांद्रता लगभग 50% (1.8 → 0.9 mg/m³) कम हुई जबकि SST जनवरी-जून अवधि में 2.7°C बढ़ा।',
    trendNarrative: 'सहसंबंध अवलोकन — पुष्टि कारण संबंध नहीं। निश्चित मूल्यांकन के लिए क्षेत्रीय मत्स्य पालन प्राधिकरणों से परामर्श करें।',
  },
};

// ── Mock responses in Marathi ───────────────────────────────
export const mockResponsesMr: Record<string, ChatMessage> = {
  safety: {
    ...mockResponses.safety,
    id: 'resp-safety-mr',
    content:
      'एकूण सेक्टर जोखीम: कमी (18/100) — परिस्थिती योग्य. पहाट आणि सकाळची वेळ (05:00 - 11:00 IST) यंत्रीकृत आणि मोटर चलित मासेमारी जहाजांसाठी (>9m) शांत समुद्री परिस्थिती उपलब्ध.',
    recommendation: 'मासेमारीची परिस्थिती सध्या योग्य आहे. निघण्यापूर्वी अधिकृत सागरी सल्ल्याचे निरीक्षण सुरू ठेवा.',
  },
  pfz: {
    ...mockResponses.pfz,
    id: 'resp-pfz-mr',
    content:
      'जवळचे PFZ ओळखले: PFZ अल्फा, सध्याच्या स्थानापासून 32 किमी. SST रीडिंग योग्य (28.2°C), क्लोरोफिल एकाग्रता जास्त (1.4 mg/m³), आणि सागरी जोखीम कमी.',
  },
  avoidance: {
    ...mockResponses.avoidance,
    id: 'resp-avoidance-mr',
    content: 'निवडलेल्या कालावधीत 3 भागांपासून दूर राहावे:',
    avoidanceZones: [
      { label: 'उंच-लाटा क्षेत्र', reason: 'उंच लाटा (2.0–2.4 मीटर) 14:00–17:30 IST' },
      { label: 'विजा चेतावणी क्षेत्र', reason: 'संवहनी क्रिया, 14:30 IST पर्यंत विजेचा धोका' },
      { label: 'प्रतिबंधित / जिओफेन्स क्षेत्र', reason: 'नौदल सराव क्षेत्र — तात्पुरते प्रतिबंधित' },
    ],
  },
  route: {
    ...mockResponses.route,
    id: 'resp-route-mr',
    content: 'शिफारस केलेला सुरक्षित मार्ग ओळखला. सरळ मार्गापासून 2° विचलन लाटांचा धोका अंदाजे 40% कमी करतो.',
  },
  productivity: {
    ...mockResponses.productivity,
    id: 'resp-productivity-mr',
    content: 'सेक्टर 4 साठी उत्पादकता ट्रेंड विश्लेषण: क्लोरोफिल एकाग्रता अंदाजे 50% (1.8 → 0.9 mg/m³) कमी झाली तर SST जानेवारी-जून काळात 2.7°C ने वाढला.',
    trendNarrative: 'सहसंबंध निरीक्षण — पुष्टी केलेला कारणात्मक संबंध नाही. निश्चित मूल्यांकनासाठी प्रादेशिक मत्स्यव्यवसाय प्राधिकरणांचा सल्ला घ्या.',
  },
};

// ── Agent Network ───────────────────────────────────────────
export const agentNetwork: AgentInfo[] = [
  { id: 'agent-ui', name: 'User Interaction', shortName: 'UI', status: 'complete', icon: 'user', latency: '12ms' },
  { id: 'agent-planner', name: 'Planner', shortName: 'PLANNER', status: 'complete', icon: 'brain', latency: '45ms' },
  { id: 'agent-marine', name: 'Marine Data', shortName: 'MARINE', status: 'complete', icon: 'anchor', latency: '120ms' },
  { id: 'agent-weather', name: 'Weather', shortName: 'WEATHER', status: 'complete', icon: 'cloudSun', latency: '89ms' },
  { id: 'agent-ocean', name: 'Ocean Analytics', shortName: 'OCEAN', status: 'complete', icon: 'waves', latency: '156ms' },
  { id: 'agent-geo', name: 'Geospatial', shortName: 'GEO', status: 'complete', icon: 'map', latency: '78ms' },
  { id: 'agent-risk', name: 'Risk Assessment', shortName: 'RISK', status: 'complete', icon: 'shieldAlert', latency: '34ms' },
  { id: 'agent-viz', name: 'Visualization', shortName: 'VIZ', status: 'complete', icon: 'barChart3', latency: '23ms' },
  { id: 'agent-report', name: 'Reporting', shortName: 'REPORT', status: 'complete', icon: 'fileText', latency: '18ms' },
];
