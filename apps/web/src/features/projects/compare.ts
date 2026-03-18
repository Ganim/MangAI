export function clampComparePosition(value: number) {
  if (Number.isNaN(value)) {
    return 50;
  }
  return Math.min(100, Math.max(0, value));
}

export function resolveComparePositionFromSliderValue(value: string) {
  return clampComparePosition(Number(value));
}

export function getCompareRevealStyle(position: number) {
  const clampedPosition = clampComparePosition(position);
  return {
    clipPath: `inset(0 ${100 - clampedPosition}% 0 0)`,
  };
}

export function getCompareDividerStyle(position: number) {
  const clampedPosition = clampComparePosition(position);
  return {
    left: `${clampedPosition}%`,
  };
}
