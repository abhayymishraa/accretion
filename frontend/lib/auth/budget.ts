/** Dollars with cents, shared by every budget display so they cannot drift. */
export function formatUsd(amount: number) {
    return `$${amount.toFixed(2)}`;
}
