import { BaseCaregiverRecordProvider } from "./providers/BaseCaregiverRecordProvider";
import type { CaregiverRecordProvider } from "./types";

export const createCaregiverRecordProvider = (): CaregiverRecordProvider =>
  new BaseCaregiverRecordProvider();
