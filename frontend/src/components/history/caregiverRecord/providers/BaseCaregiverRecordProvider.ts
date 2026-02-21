import type { TrendRangeKey } from "@/composables/useTrendRange";
import { buildCaregiverRecordModel } from "../buildCaregiverRecordModel";
import type { CaregiverRecordPageModel, CaregiverRecordProvider } from "../types";

export class BaseCaregiverRecordProvider implements CaregiverRecordProvider {
  async getRecord(range: TrendRangeKey): Promise<CaregiverRecordPageModel> {
    return buildCaregiverRecordModel(range);
  }
}
