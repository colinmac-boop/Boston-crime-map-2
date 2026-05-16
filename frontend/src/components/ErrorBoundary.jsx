import { Component } from "react";

export default class ErrorBoundary extends Component {
    constructor(props) {
        super(props);
        this.state = { error: null };
    }

    static getDerivedStateFromError(error) {
        return { error };
    }

    componentDidCatch(error, info) {
        // eslint-disable-next-line no-console
        console.error("[ErrorBoundary]", error, info?.componentStack);
    }

    reset = () => {
        this.setState({ error: null });
    };

    render() {
        if (!this.state.error) return this.props.children;

        return (
            <main
                className="max-w-2xl mx-auto px-5 py-16 paperdrop"
                data-testid="error-boundary"
            >
                <div className="kicker">Section · Stop the Presses</div>
                <h1 className="headline-xl text-4xl sm:text-5xl md:text-7xl mt-2">
                    Something fell off the back of the truck.
                </h1>
                <p className="font-display italic text-lg sm:text-xl text-[var(--muted)] mt-3 leading-snug">
                    The page errored out. Not your fault, not ours either — probably a bit of both. Try reloading.
                </p>
                <div className="mt-6 flex flex-wrap gap-3">
                    <button
                        className="btn-ink"
                        onClick={() => window.location.reload()}
                        data-testid="error-reload"
                    >
                        Reload the page
                    </button>
                    <a className="btn-ghost" href="/" data-testid="error-home">
                        Back to the front page
                    </a>
                </div>
                {process.env.NODE_ENV !== "production" && this.state.error && (
                    <pre className="mt-6 p-4 border-2 border-[var(--ink)] bg-[var(--surface)] font-mono text-xs overflow-x-auto">
                        {String(this.state.error?.stack || this.state.error)}
                    </pre>
                )}
            </main>
        );
    }
}
