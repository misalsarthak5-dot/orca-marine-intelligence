'use client';

import React, { useState, useRef, useEffect } from 'react';
import {
  Mic,
  Send,
  CheckCircle2,
  ArrowRight,
  Sparkles,
  MapPin,
  Shield,
  Navigation,
  BarChart3,
  AlertTriangle,
  TrendingDown,
} from 'lucide-react';
import { useTranslation } from '@/lib/i18n';
import { useLocation } from '@/lib/location';
import { processQueryAsync } from '@/services/orcaService';
import { ChatMessage, ChatAttachment, MapLayerType, TranslationStrings } from '@/types';
import { suggestionChips } from '@/data/mockConversations';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';

interface AskOrcaProps {
  onLayerActivate?: (layers: MapLayerType[]) => void;
}

const categories = [
  { label: 'cat_marineIntelligence', icon: <Sparkles size={11} />, color: 'bg-teal-600 text-white' },
  { label: 'cat_pfzDiscovery', icon: <MapPin size={11} />, color: 'bg-navy-100 text-navy-700' },
  { label: 'cat_safetyAssessment', icon: <Shield size={11} />, color: 'bg-navy-100 text-navy-700' },
  { label: 'cat_routeIntelligence', icon: <Navigation size={11} />, color: 'bg-navy-100 text-navy-700' },
];

const orcaReasoningStages = [
  'Understanding request',
  'Planning',
  'Weather Intelligence',
  'Marine Intelligence',
  'Risk Assessment',
  'Recommendation',
];

export default function AskOrca({ onLayerActivate }: AskOrcaProps) {
  const { t, language } = useTranslation();
  const { selectedLocation } = useLocation();
  const [query, setQuery] = useState('');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [activeStep, setActiveStep] = useState(-1);
  const [userQuery, setUserQuery] = useState('');
  const responseRef = useRef<HTMLDivElement>(null);

  const handleAttachmentClick = (att: ChatAttachment, msg: ChatMessage) => {
    if (att.type === 'safety') {
      const el = document.getElementById('orca-safety-assessment');
      if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'center' });
        el.classList.add('ring-2', 'ring-teal-500');
        setTimeout(() => el.classList.remove('ring-2', 'ring-teal-500'), 2500);
      }
      return;
    }

    const layers = att.layers || msg.mapActions || (att.type === 'pfz' ? ['pfz'] : att.type === 'route' ? ['route', 'risk'] : ['risk']);
    onLayerActivate?.(layers);

    const mapEl = document.getElementById('orca-marine-map');
    if (mapEl) {
      mapEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  };

  const handleSubmit = (q: string) => {
    if (!q.trim()) return;

    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: q,
      timestamp: new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Kolkata' }) + ' IST',
    };

    setMessages((prev) => [...prev, userMsg]);
    setUserQuery(q);
    setQuery('');
    setIsProcessing(true);
    setActiveStep(0);

    // Progression through the 6 ORCA reasoning stages
    let step = 0;
    const interval = setInterval(() => {
      step++;
      setActiveStep(step);
      if (step >= orcaReasoningStages.length - 1) {
        clearInterval(interval);
        setTimeout(async () => {
          try {
            const response = await processQueryAsync(q, language, selectedLocation);
            if (response) {
              setMessages((prev) => [...prev, response]);

              if (response.intent === 'fishing_safety') {
                const qLower = q.toLowerCase();
                const isTomorrowMorning = qLower.includes('tomorrow morning') || qLower.includes('कल सुबह') || qLower.includes('उद्या सकाळी');
                const isTomorrow = qLower.includes('tomorrow') || qLower.includes('कल') || qLower.includes('उद्या');
                const targetWindow = isTomorrowMorning ? 'tomorrow_morning' : isTomorrow ? 'tomorrow' : 'now';
                window.dispatchEvent(new CustomEvent('orca:safety-sync', {
                  detail: { timeWindow: targetWindow }
                }));
              }

              // Automatically activate map layer if response has map actions
              if (response.mapActions && response.mapActions.length > 0) {
                onLayerActivate?.(response.mapActions);
              }
            }
          } catch (err) {
            console.error('Ask ORCA query processing error:', err);
          } finally {
            setIsProcessing(false);
            setActiveStep(-1);
          }
        }, 350);
      }
    }, 280);
  };

  useEffect(() => {
    if (messages.length > 0 && responseRef.current) {
      responseRef.current.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }, [messages]);

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-100">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-[13px] font-bold text-navy-900">{t('ask_title')} • {t('ask_subtitle')}</h3>
            <p className="text-[11px] text-gray-500 mt-0.5">
              Ask about fishing safety, PFZs, marine conditions, routes, hazards, or restricted zones.
            </p>
          </div>
          <span className="text-[10px] font-semibold text-teal-800 bg-teal-50 px-2.5 py-1 rounded-full border border-teal-200">
            Sector: {selectedLocation.name} ({selectedLocation.latitude.toFixed(2)}°N, {selectedLocation.longitude.toFixed(2)}°E)
          </span>
        </div>
        {/* Category pills */}
        <div className="flex items-center gap-1.5 mt-2.5">
          {categories.map((cat, i) => (
            <span
              key={i}
              className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] font-semibold ${cat.color}`}
            >
              {cat.icon}
              {t(cat.label as keyof TranslationStrings)}
            </span>
          ))}
        </div>
      </div>

      {/* Messages area */}
      {messages.length > 0 && (
        <div className="px-4 py-3 border-b border-gray-100 max-h-[480px] overflow-y-auto space-y-3 scrollbar-thin">
          {messages.map((msg) => (
            <div
              key={msg.id}
              ref={responseRef}
              className={`animate-fade-in ${msg.role === 'user' ? 'flex justify-end' : ''}`}
            >
              {msg.role === 'user' ? (
                <div className="inline-block bg-navy-900 text-white px-4 py-2 rounded-xl rounded-br-sm text-[12px] max-w-[80%] shadow-xs">
                  {msg.content}
                </div>
              ) : (
                <div className="space-y-2.5 bg-slate-50/50 p-3 rounded-xl border border-slate-100">
                  {/* Verdict badge */}
                  {msg.verdictTitle && (
                    <div className="inline-flex items-center gap-1.5 bg-teal-50 border border-teal-200 text-teal-800 px-3 py-1 rounded-full text-[10px] font-bold">
                      <CheckCircle2 size={12} className="text-teal-600" />
                      {msg.verdictTitle}
                    </div>
                  )}

                  {/* Content */}
                  <p className="text-[12px] text-navy-800 leading-relaxed whitespace-pre-line">{msg.content}</p>

                  {/* ORCA Reasoning Workflow Execution Trace */}
                  {msg.workflowStages && msg.workflowStages.length > 0 && (
                    <div className="mt-2 bg-white border border-slate-200 rounded-lg p-2.5 shadow-xs">
                      <p className="text-[10px] font-bold text-slate-700 uppercase tracking-wider mb-1.5 flex items-center gap-1.5">
                        <Sparkles size={11} className="text-teal-600" />
                        ORCA Reasoning Workflow
                      </p>
                      <div className="space-y-1">
                        {msg.workflowStages.map((ws, idx) => (
                          <div key={idx} className="flex items-start gap-1.5 text-[10px]">
                            <CheckCircle2 size={11} className="text-teal-600 mt-0.5 flex-shrink-0" />
                            <span className="font-semibold text-slate-800">{ws.stage}:</span>
                            <span className="text-slate-600">{ws.detail}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Factors */}
                  {msg.factors && msg.factors.length > 0 && (
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mt-2">
                      {msg.factors.map((f) => (
                        <div key={f.id} className="bg-white border border-gray-100 p-2 rounded-lg text-[10px]">
                          <p className="font-semibold text-navy-700">{t(f.label as keyof TranslationStrings) || f.label}</p>
                          <p className={`font-bold mt-0.5 ${f.statusColor === 'green' ? 'text-green-600' : f.statusColor === 'amber' ? 'text-amber-600' : 'text-red-600'}`}>
                            {f.value}
                          </p>
                          <p className="text-[9px] text-gray-400 mt-0.5">{f.status}</p>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* PFZ info */}
                  {msg.pfz && (
                    <div className="bg-teal-50 border border-teal-200 rounded-lg p-3 mt-2">
                      <div className="flex items-center justify-between mb-2">
                        <h4 className="text-[12px] font-bold text-teal-800">{msg.pfz.name}</h4>
                        <span className="text-[10px] text-teal-600 font-semibold">{msg.pfz.distance} • Bearing: 240° WSW</span>
                      </div>
                      <div className="grid grid-cols-2 gap-1.5 text-[10px] text-navy-700">
                        <span>SST: {msg.pfz.sst}</span>
                        <span>Chlorophyll: {msg.pfz.chlorophyll}</span>
                        <span>Risk: {msg.pfz.marineRisk}</span>
                        <span>Dataset: Demo / Satellite Dataset</span>
                      </div>
                    </div>
                  )}

                  {/* Avoidance zones */}
                  {msg.avoidanceZones && (
                    <div className="space-y-1.5 mt-2">
                      {msg.avoidanceZones.map((zone, i) => (
                        <div key={i} className="flex items-start gap-2 p-2 bg-red-50 border border-red-100 rounded-lg">
                          <AlertTriangle size={12} className="text-red-500 mt-0.5 flex-shrink-0" />
                          <div>
                            <p className="text-[11px] font-semibold text-red-700">{zone.label}</p>
                            <p className="text-[10px] text-red-600">{zone.reason}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Trend chart */}
                  {msg.trendData && (
                    <div className="mt-2 bg-white border border-gray-200 rounded-lg p-3">
                      <h4 className="text-[11px] font-bold text-navy-800 mb-2 flex items-center gap-1">
                        <TrendingDown size={12} className="text-amber-500" />
                        Productivity Trend — SST vs Chlorophyll
                      </h4>
                      <div className="h-[160px]">
                        <ResponsiveContainer width="100%" height="100%">
                          <LineChart data={msg.trendData}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                            <XAxis dataKey="month" tick={{ fontSize: 10, fill: '#64748b' }} />
                            <YAxis yAxisId="left" tick={{ fontSize: 10, fill: '#64748b' }} />
                            <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 10, fill: '#64748b' }} />
                            <Tooltip contentStyle={{ fontSize: 11, fontFamily: 'Inter' }} />
                            <Legend wrapperStyle={{ fontSize: 10 }} />
                            <Line yAxisId="left" type="monotone" dataKey="sst" stroke="#ef4444" strokeWidth={2} dot={{ r: 3 }} name="SST (°C)" />
                            <Line yAxisId="right" type="monotone" dataKey="chlorophyll" stroke="#22c55e" strokeWidth={2} dot={{ r: 3 }} name="Chl (mg/m³)" />
                          </LineChart>
                        </ResponsiveContainer>
                      </div>
                    </div>
                  )}

                  {/* Recommendation */}
                  {msg.recommendation && (
                    <div className="bg-white border border-gray-200 rounded-lg p-2.5 mt-2">
                      <p className="text-[10px] font-bold text-navy-800 uppercase tracking-wider mb-1">Recommendation</p>
                      <p className="text-[11px] text-gray-700 leading-relaxed">{msg.recommendation}</p>
                    </div>
                  )}

                  {/* Attachment action buttons */}
                  {msg.attachments && msg.attachments.length > 0 && (
                    <div className="flex flex-wrap gap-2 mt-2 pt-1">
                      {msg.attachments.map((att, i) => (
                        <button
                          key={i}
                          onClick={() => handleAttachmentClick(att, msg)}
                          className="inline-flex items-center gap-1 px-3 py-1.5 bg-teal-50 text-teal-700 text-[10px] font-semibold rounded-lg border border-teal-200 hover:bg-teal-100 hover:border-teal-300 transition-colors cursor-pointer"
                        >
                          {att.label}
                          <ArrowRight size={10} />
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Input area */}
      <div className="px-4 py-3">
        <div className="flex items-center gap-2">
          <div className="flex-1 relative">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSubmit(query)}
              placeholder={t('ask_placeholder')}
              className="w-full pl-4 pr-10 py-2.5 bg-gray-50 border border-gray-200 rounded-xl text-[12px] text-navy-800 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-teal-500/30 focus:border-teal-400 focus:bg-white transition-all"
            />
            <button className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600">
              <Mic size={14} />
            </button>
          </div>
          <button
            onClick={() => handleSubmit(query)}
            disabled={isProcessing}
            className="px-4 py-2.5 bg-teal-600 text-white text-[11px] font-semibold rounded-xl hover:bg-teal-700 transition-colors disabled:opacity-50 flex items-center gap-1.5 cursor-pointer"
          >
            {t('ask_query')}
            <Send size={12} />
          </button>
        </div>

        {/* Suggestion chips */}
        <div className="flex items-center gap-1.5 mt-2.5 flex-wrap">
          <span className="text-[10px] text-gray-400 font-semibold uppercase tracking-wider mr-1">
            {t('ask_suggestedFor')}
          </span>
          {suggestionChips.map((chip) => (
            <button
              key={chip.id}
              onClick={() => handleSubmit(t(chip.label as keyof TranslationStrings))}
              disabled={isProcessing}
              className="px-2.5 py-1 bg-gray-100 text-navy-700 text-[10px] font-medium rounded-lg border border-gray-200 hover:bg-teal-50 hover:border-teal-200 hover:text-teal-700 transition-colors disabled:opacity-50 cursor-pointer"
            >
              &ldquo;{t(chip.label as keyof TranslationStrings)}&rdquo;
            </button>
          ))}
        </div>
      </div>

      {/* Pipeline visualization */}
      {isProcessing && (
        <div className="px-4 pb-3">
          <div className="flex items-center justify-between mb-1.5 px-0.5">
            <span className="text-[10px] font-bold text-teal-800 uppercase tracking-wider flex items-center gap-1.5">
              <Sparkles size={11} className="text-teal-600 animate-spin" />
              ORCA Reasoning Workflow
            </span>
            <span className="text-[9px] text-gray-500 font-medium">
              Analyzing coastal telemetry...
            </span>
          </div>
          <div className="flex items-center gap-1 bg-gray-50 rounded-lg p-2 overflow-x-auto">
            {orcaReasoningStages.map((stage, i) => (
              <React.Fragment key={stage}>
                <div
                  className={`flex items-center gap-1 px-2 py-1 rounded text-[9px] font-bold tracking-tight whitespace-nowrap transition-all duration-300 ${
                    i <= activeStep
                      ? 'bg-teal-600 text-white'
                      : 'bg-gray-200 text-gray-400'
                  }`}
                >
                  {i <= activeStep && <CheckCircle2 size={9} />}
                  {stage}
                </div>
                {i < orcaReasoningStages.length - 1 && (
                  <ArrowRight size={10} className={i < activeStep ? 'text-teal-500' : 'text-gray-300'} />
                )}
              </React.Fragment>
            ))}
          </div>
        </div>
      )}

      {/* Response with pipeline context */}
      {isProcessing && userQuery && (
        <div className="px-4 pb-3">
          <div className="bg-teal-50 border border-teal-200 rounded-lg px-3 py-2">
            <p className="text-[10px] text-teal-700">
              <span className="font-bold">Query:</span> &ldquo;{userQuery}&rdquo;
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
