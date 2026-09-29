export type DeadlineBand = Readonly<{
  id: string;
  label: string;
  maxDays: number;
  fillToken: string;
  textToken: string;
}>;

export const DEADLINE_BANDS: readonly DeadlineBand[];
export const NULL_DEADLINE_HATCH: string;

export function deadlineBand(days: number | null): DeadlineBand | null;

export function tileFill(days: number | null): {
  band: DeadlineBand | null;
  style: {
    backgroundImage?: string;
    backgroundColor?: string;
    color: string;
  };
};

export function nullDeadlineLabel(state: string): string;
