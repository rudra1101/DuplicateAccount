export function stringSimilarity(a: string, b: string): number {

    a = a.toLowerCase();
    b = b.toLowerCase();

    if (a === b) return 1;

    let matches = 0;

    const len = Math.min(a.length, b.length);

    for (let i = 0; i < len; i++) {

        if (a[i] === b[i])
            matches++;

    }

    return matches / Math.max(a.length, b.length);
}