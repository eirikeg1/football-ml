/** Reactive state for the training view. */

import type {
  TrainingConfig,
  TrainingStatus,
  EpochResult,
  ResourceUsage,
} from "./training-types";
import { DEFAULT_TRAINING_CONFIG } from "./training-types";

export const trainingState = $state({
  config: { ...DEFAULT_TRAINING_CONFIG } as TrainingConfig,
  status: "idle" as TrainingStatus,
  currentEpoch: 0,
  totalEpochs: 0,
  trainLoss: [] as number[],
  valLoss: [] as number[],
  metrics: {} as Record<string, number[]>,
  currentLR: 0,
  bestMetric: 0,
  logs: [] as { level: string; message: string; timestamp: string }[],
  wsConnected: false,
  resources: null as ResourceUsage | null,
  startedAt: 0,              // timestamp (ms) when training started
  epochTimes: [] as number[], // elapsed_seconds per epoch
});

export function resetTraining(): void {
  trainingState.status = "idle";
  trainingState.currentEpoch = 0;
  trainingState.totalEpochs = 0;
  trainingState.trainLoss = [];
  trainingState.valLoss = [];
  trainingState.metrics = {};
  trainingState.currentLR = 0;
  trainingState.bestMetric = 0;
  trainingState.logs = [];
  trainingState.startedAt = Date.now();
  trainingState.epochTimes = [];
}

export function updateFromEpochResult(result: EpochResult): void {
  trainingState.currentEpoch = result.epoch;
  trainingState.trainLoss = [...trainingState.trainLoss, result.train_loss];
  trainingState.valLoss = [...trainingState.valLoss, result.val_loss];
  trainingState.currentLR = result.learning_rate;
  trainingState.bestMetric = result.best_metric;
  trainingState.resources = result.resources ?? null;
  trainingState.epochTimes = [...trainingState.epochTimes, result.elapsed_seconds];

  // Update per-metric history
  for (const [name, value] of Object.entries(result.metrics)) {
    const history = trainingState.metrics[name] ?? [];
    trainingState.metrics = {
      ...trainingState.metrics,
      [name]: [...history, value],
    };
  }
}

export function appendLog(level: string, message: string): void {
  const timestamp = new Date().toLocaleTimeString();
  trainingState.logs = [
    ...trainingState.logs,
    { level, message, timestamp },
  ];
}

export function setStatus(status: TrainingStatus): void {
  trainingState.status = status;
}
