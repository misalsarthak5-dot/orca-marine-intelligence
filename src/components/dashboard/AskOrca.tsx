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
import { processQuery, processQueryAsync } from '@/services/orcaService';
import { ChatMessage, MapLayerType, TranslationStrings } from '@/types';
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

const pipelineSteps = [
  'pipeline_ask',
  'pipeline_plan',
  'pipeline_retrieve',
  'pipeline_reason',
  'pipeline_recommend',
  'pipeline_explain',
];

export default function AskOrca({ onLayerActivate }: AskOrcaProps) {
  const { t, language } = useTranslation();
  const [query, setQuery] = useState('');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [activeStep, setActiveStep] = useState(-1);
  const [userQuery, setUserQuery] = useState('');
  const responseRef = useRef<HTMLDivElement>(null);

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

    // Simulate pipeline progression
    let step = 0;
    const interval = setInterval(() => {
      step++;
      setActiveStep(step);
      if (step >= pipelineSteps.length - 1) {
        clearInterval(interval);
        setTimeout(async () => {
          const response = await processQueryAsync(q, language);
          if (response) {
            setMessages((prev) => [...prev, response]);
            // Activate relevant map layers
            const ql = q.toLowerCase();
            if (ql.includes('pfz') || ql.includes('nearest') || ql.includes('निकटतम') || ql.includes('जवळ')) {
              onLayerActivate?.(['pfz']);
            } else if (ql.includes('avoid') || ql.includes('बचना') || ql.includes('दूर')) {
              onLayerActivate?.(['risk', 'geofence']);
            } else if (ql.includes('route') || ql.includes('safest') || ql.includes('मार्ग')) {
              onLayerActivate?.(['route', 'risk']);
            } else if (ql.includes('safe') || ql.includes('सुरक्षित') || ql.includes('सुरक्षा')) {
              onLayerActivate?.(['risk']);
            }
          }
          setIsProcessing(false);
          setActiveStep(-1);
        }, 400);
      }
    }, 350);
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
        <div className="px-4 py-3 border-b border-gray-100 max-h-[400px] overflow-y-auto space-y-3">
          {messages.map((msg) => (
            <div
              key={msg.id}
              ref={responseRef}
              className={`animate-fade-in ${msg.role === 'user' ? 'flex justify-end' : ''}`}
            >
              {msg.role === 'user' ? (
                <div className="inline-block bg-navy-900 text-white px-4 py-2 rounded-xl rounded-br-sm text-[12px] max-w-[80%]">
                  {msg.content}
                </div>
              ) : (
                <div className="space-y-2.5">
                  {/* Verdict badge */}
                  {msg.verdictTitle && (
                    <div className="inline-flex items-center gap-1.5 bg-green-50 border border-green-200 text-green-700 px-3 py-1 rounded-full text-[10px] font-bold">
                      <CheckCircle2 size={12} />
                      {msg.verdictTitle}
                    </div>
                  )}

                  {/* Content */}
                  <p className="text-[12px] text-navy-800 leading-relaxed">{msg.content}</p>

                  {/* Factors */}
                  {msg.factors && (
                    <div className="grid grid-cols-3 gap-2 mt-2">
                      {msg.factors.map((f) => (
                        <div key={f.id} className="flex items-center gap-1.5 text-[10px]">
                          <span className="font-semibold text-navy-700">{t(f.label as keyof TranslationStrings)}</span>
                          <span className={`font-medium ${f.statusColor === 'green' ? 'text-green-600' : f.statusColor === 'amber' ? 'text-amber-600' : 'text-red-600'}`}>
                            {f.value}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* PFZ info */}
                  {msg.pfz && (
                    <div className="bg-teal-50 border border-teal-200 rounded-lg p-3 mt-2">
                      <div className="flex items-center justify-between mb-2">
                        <h4 className="text-[12px] font-bold text-teal-700">{msg.pfz.name}</h4>
                        <span className="text-[10px] text-teal-600 font-semibold">{msg.pfz.distance} • Bearing: 242°</span>
                      </div>
                      <div className="grid grid-cols-2 gap-1.5 text-[10px] text-navy-700">
                        <span>SST: {msg.pfz.sst} — {msg.pfz.sstStatus}</span>
                        <span>Chlorophyll: {msg.pfz.chlorophyll} — {msg.pfz.chlorophyllStatus}</span>
                        <span>Risk: {msg.pfz.marineRisk}</span>
                        <span>Probability: {msg.pfz.probability}</span>
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
                    <div className="mt-2 bg-gray-50 border border-gray-200 rounded-lg p-3">
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
                      {msg.trendNarrative && (
                        <p className="text-[10px] text-amber-600 italic mt-2 flex items-start gap-1">
                          <AlertTriangle size={10} className="flex-shrink-0 mt-0.5" />
                          {msg.trendNarrative}
                        </p>
                      )}
                    </div>
                  )}

                  {/* Recommendation */}
                  {msg.recommendation && (
                    <div className="bg-gray-50 border border-gray-200 rounded-lg p-2.5 mt-2">
                      <p className="text-[10px] font-bold text-navy-800 uppercase tracking-wider mb-1">Recommendation</p>
                      <p className="text-[11px] text-gray-600">{msg.recommendation}</p>
                    </div>
                  )}

                  {/* Attachment buttons */}
                  {msg.attachments && (
                    <div className="flex gap-2 mt-2">
                      {msg.attachments.map((att, i) => (
                        <button
                          key={i}
                          className="inline-flex items-center gap-1 px-3 py-1.5 bg-teal-50 text-teal-700 text-[10px] font-semibold rounded-lg border border-teal-200 hover:bg-teal-100 transition-colors"
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
            className="px-4 py-2.5 bg-teal-600 text-white text-[11px] font-semibold rounded-xl hover:bg-teal-700 transition-colors disabled:opacity-50 flex items-center gap-1.5"
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
              className="px-2.5 py-1 bg-gray-100 text-navy-700 text-[10px] font-medium rounded-lg border border-gray-200 hover:bg-teal-50 hover:border-teal-200 hover:text-teal-700 transition-colors disabled:opacity-50"
            >
              &ldquo;{t(chip.label as keyof TranslationStrings)}&rdquo;
            </button>
          ))}
        </div>
      </div>

      {/* Pipeline visualization */}
      {isProcessing && (
        <div className="px-4 pb-3">
          <div className="flex items-center gap-1 bg-gray-50 rounded-lg p-2">
            {pipelineSteps.map((step, i) => (
              <React.Fragment key={step}>
                <div
                  className={`flex items-center gap-1 px-2 py-1 rounded text-[9px] font-bold uppercase tracking-wider transition-all duration-300 ${
                    i <= activeStep
                      ? 'bg-teal-600 text-white'
                      : 'bg-gray-200 text-gray-400'
                  }`}
                >
                  {i <= activeStep && <CheckCircle2 size={9} />}
                  {t(step as keyof TranslationStrings)}
                </div>
                {i < pipelineSteps.length - 1 && (
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
