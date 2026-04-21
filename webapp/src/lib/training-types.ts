/** TypeScript interfaces for training configuration and WebSocket messages. */

export interface TrainingConfig {
  optimizer: "adam" | "sgd" | "adamw";
  learning_rate: number;
  weight_decay: number;
  epochs: number;
  batch_size: number;
  val_split: number;
  early_stopping_patience: number;
  heads: string[];
  loss_overrides: Record<string, string>;
  loss_weights: Record<string, number>;
  metrics: string[];
  scheduler: "step" | "cosine" | "warmup" | null;
  scheduler_params: Record<string, number>;
  checkpoint_dir: string;
}

export type TrainingStatus =
  | "idle"
  | "training"
  | "paused"
  | "completed"
  | "error";

export interface ResourceUsage {
  ram_used_gb: number;
  ram_total_gb: number;
  ram_percent: number;
  gpu_vram_used_gb: number;
  gpu_vram_total_gb: number;
  gpu_vram_percent: number;
  gpu_name: string;
  cpu_percent: number;
}

export interface EpochResult {
  type: "epoch";
  epoch: number;
  train_loss: number;
  val_loss: number;
  learning_rate: number;
  metrics: Record<string, number>;
  best_metric: number;
  is_best: boolean;
  elapsed_seconds: number;
  resources?: ResourceUsage;
}

export interface StatusMessage {
  type: "status";
  status: TrainingStatus;
  message?: string;
}

export interface LogMessage {
  type: "log";
  level: "info" | "warning" | "error";
  message: string;
}

export type WSMessage = EpochResult | StatusMessage | LogMessage;

export interface LossOptions {
  default: string;
  options: string[];
}

export const DEFAULT_TRAINING_CONFIG: TrainingConfig = {
  optimizer: "adam",
  learning_rate: 0.001,
  weight_decay: 0,
  epochs: 50,
  batch_size: 32,
  val_split: 0.2,
  early_stopping_patience: 10,
  heads: ["match_outcome"],
  loss_overrides: {},
  loss_weights: {},
  metrics: ["accuracy"],
  scheduler: null,
  scheduler_params: {},
  checkpoint_dir: "checkpoints",
};
