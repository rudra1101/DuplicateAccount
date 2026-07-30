import { Account } from "../models/Account";
import { stringSimilarity } from "./similarity";

export interface DuplicateResult {

    account1: Account;

    account2: Account;

    confidence: number;

}

export function detectDuplicates(
    accounts: Account[]
): DuplicateResult[] {

    const results: DuplicateResult[] = [];

    for (let i = 0; i < accounts.length; i++) {

        for (let j = i + 1; j < accounts.length; j++) {

            const a = accounts[i];
            const b = accounts[j];

            const nameScore =
                (
                    stringSimilarity(a.firstName, b.firstName) +
                    stringSimilarity(a.lastName, b.lastName)
                ) / 2;

            const emailScore =
                stringSimilarity(a.email, b.email);

            const usernameScore =
                stringSimilarity(a.username, b.username);

            const score =
                (
                    nameScore * 0.5 +
                    emailScore * 0.3 +
                    usernameScore * 0.2
                );

            if (score > 0.70) {

                results.push({

                    account1: a,

                    account2: b,

                    confidence: Math.round(score * 100)

                });

            }

        }

    }

    return results;

}