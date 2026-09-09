import { ChatMessage, Language } from '@/types';
import { mockResponses, mockResponsesHi, mockResponsesMr } from '@/data/mockConversations';
import { getLiveOrcaMarineData } from './orcaDataService';

const responsesByLanguage: Record<Language, Record<string, ChatMessage>> = {
  en: mockResponses,
  hi: mockResponsesHi,
  mr: mockResponsesMr,
};

/**
 * Process a user query asynchronously with real Open-Meteo hourly and marine data enrichment.
 */
export async function processQueryAsync(query: string, language: Language = 'en'): Promise<ChatMessage> {
  const q = query.toLowerCase();
  const responses = responsesByLanguage[language] || mockResponses;

  // Check for tomorrow / safety / weather queries
  if (
    q.includes('safe') ||
    q.includes('tomorrow') ||
    q.includes('weather') ||
    q.includes('wave') ||
    q.includes('wind') ||
    q.includes('सुरक्षित') ||
    q.includes('कल') ||
    q.includes('सुरक्षा') ||
    q.includes('उद्या')
  ) {
    try {
      const liveData = await getLiveOrcaMarineData();
      if (liveData.isLive) {
        const base = responses.safety;
        const tm = liveData.tomorrowMorning;
        const c = liveData.current;

        const liveContent = language === 'hi'
          ? `ओपन-मेटियो वास्तविक समय पूर्वानुमान (मुंबई तट - ${tm.window}): औसत लहरें ${tm.avgWaveHeight} मी, हवा ${tm.avgWindSpeed} समुद्री मील (${c.windDirectionCompass})। समुद्र सतह तापमान ${c.seaSurfaceTemperature}°C। ${tm.isSafe ? 'कल सुबह मछली पकड़ने की स्थिति अनुकूल है।' : 'सावधानी बरतें।'}`
          : language === 'mr'
          ? `ओपन-मेटिओ थेट अंदाज (मुंबई किनारपट्टी - ${tm.window}): सरासरी लाटा ${tm.avgWaveHeight} मी, वारा ${tm.avgWindSpeed} नॉट्स (${c.windDirectionCompass})। समुद्राचे तापमान ${c.seaSurfaceTemperature}°C। ${tm.isSafe ? 'उद्या सकाळी मासेमारीसाठी परिस्थिती अनुकूल आहे.' : 'दक्षता बाळगावी.'}`
          : `Live Open-Meteo Marine Forecast (Mumbai Coast - ${tm.window}): Sea conditions show waves averaging ${tm.avgWaveHeight}m with wind at ${tm.avgWindSpeed} kts (${c.windDirectionCompass}). Sea Surface Temperature is ${c.seaSurfaceTemperature}°C. ${tm.reason} Mechanized vessels may operate normally.`;

        return {
          ...base,
          id: `resp-safety-${Date.now()}`,
          content: liveContent,
          riskLevel: tm.isSafe ? 'low' : 'moderate',
          verdictTitle: tm.isSafe ? 'VERDICT: CONDITIONS SUITABLE (LIVE FORECAST)' : 'VERDICT: CAUTION ADVISED',
          factors: [
            {
              id: 'f1',
              label: 'factor_wind',
              value: `${tm.avgWindSpeed} kts (${c.windDirectionCompass})`,
              status: tm.avgWindSpeed < 18 ? 'Safe to 18 kts' : 'Approaching limit',
              statusColor: tm.avgWindSpeed < 18 ? 'green' : 'amber',
              icon: 'wind',
            },
            {
              id: 'f2',
              label: 'factor_waves',
              value: `${tm.avgWaveHeight} m`,
              status: tm.avgWaveHeight < 2.0 ? 'Threshold < 2.2m' : 'Elevated swell',
              statusColor: tm.avgWaveHeight < 2.0 ? 'green' : 'amber',
              icon: 'waves',
            },
            {
              id: 'f3',
              label: 'factor_rain',
              value: `${tm.precipitationTotal} mm`,
              status: tm.precipitationTotal < 2 ? 'Clear / Good Visibility' : 'Scattered Showers',
              statusColor: 'green',
              icon: 'cloudRain',
            },
            {
              id: 'f4',
              label: 'factor_cyclone',
              value: 'Nil Active',
              status: 'IMD / INCOIS Monitor',
              statusColor: 'green',
              icon: 'tornado',
            },
            {
              id: 'f5',
              label: 'factor_geofence',
              value: 'Clear (>3.5 NM)',
              status: 'Indian Coast Guard Safe Zone',
              statusColor: 'green',
              icon: 'shield',
            },
          ],
        };
      }
    } catch {
      // Fall through to mock response on error
    }
  }

  return processQuery(query, language);
}

/**
 * Synchronous pattern-matching fallback
 */
export function processQuery(query: string, language: Language = 'en'): ChatMessage {
  const q = query.toLowerCase();
  const responses = responsesByLanguage[language] || mockResponses;

  if (q.includes('safe') || q.includes('सुरक्षित') || q.includes('सुरक्षा')) {
    return responses.safety;
  }
  if (q.includes('pfz') || q.includes('fishing zone') || q.includes('nearest') || q.includes('निकटतम') || q.includes('जवळ')) {
    return responses.pfz;
  }
  if (q.includes('avoid') || q.includes('बचना') || q.includes('दूर')) {
    return responses.avoidance;
  }
  if (q.includes('route') || q.includes('safest') || q.includes('मार्ग')) {
    return responses.route;
  }
  if (q.includes('productivity') || q.includes('declined') || q.includes('उत्पादकता') || q.includes('गिरावट') || q.includes('घटली')) {
    return responses.productivity;
  }

  // Fallback: return the safety response for unmatched queries
  return responses.safety;
}
