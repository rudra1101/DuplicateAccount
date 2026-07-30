import { AIResponse } from "../models/chat";

export async function askAI(
    prompt: string
): Promise<AIResponse> {

    await new Promise((resolve) =>
        setTimeout(resolve, 1200)
    );

    const response =
        getMockResponse(prompt);

    return {
        message: response,
    };
}

function getMockResponse(prompt: string): string {

    const question = prompt.toLowerCase();

    if (question.includes("duplicate")) {
        return `
I found multiple duplicate account groups.

• Active Directory : 78

• Entra ID : 42

• SAP : 18

Recommendation:

Start reviewing the Active Directory duplicates since they represent the highest risk.
`;
    }

    if (question.includes("confidence")) {
        return `
The AI confidence score is calculated using:

✔ Employee ID

✔ Email Address

✔ Username Similarity

✔ Department

✔ Manager

✔ Account Attributes

The current model confidence is 98.2%.
`;
    }

    if (question.includes("report")) {
        return `
Generated Summary

Accounts Scanned : 184,265

Duplicates Found : 2,861

Pending Reviews : 464

High Risk : 32
`;
    }

    return `
I'm IdentityAI Copilot.

I can help you with duplicate account analysis, AI explanations, reports and IAM governance.
`;
}