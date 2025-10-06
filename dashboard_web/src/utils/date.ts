import { format } from "date-fns";

const DISPLAY_FORMAT = "dd-MMM-yyyy";

export function formatDisplayDate(value: string | Date | null | undefined): string {
  if (!value) {
    return "-";
  }
  const parsed = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return "-";
  }
  return format(parsed, DISPLAY_FORMAT);
}
