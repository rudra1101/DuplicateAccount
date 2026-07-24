import { accounts } from "../data/sampleAccounts";
import { detectDuplicates } from "../ai/duplicateEngine";

export const duplicateResults =
    detectDuplicates(accounts);