// Height animation lives in app/globals.css, keyed off data-faq. Nothing here
// needs to run on the client.
export function FaqItem({ question, answer }: { question: string; answer: string }) {
    return (
        <details data-faq>
            <summary>
                {question}
                <span aria-hidden="true">+</span>
            </summary>
            <p>{answer}</p>
        </details>
    );
}
