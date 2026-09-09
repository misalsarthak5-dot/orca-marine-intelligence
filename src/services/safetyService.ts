import { currentSafetyAssessment, safetyAssessments } from '@/data/mockSafetyData';
import { SafetyAssessment, RiskLevel } from '@/types';

export function getSafetyAssessment(): SafetyAssessment {
  return currentSafetyAssessment;
}

export function getSafetyAssessmentByLevel(level: RiskLevel): SafetyAssessment {
  return safetyAssessments[level];
}

export function getRiskFactors() {
  return currentSafetyAssessment.factors;
}
