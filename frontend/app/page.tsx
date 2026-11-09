import {
  ArrowDown,
  ArrowRight,
  Check,
  CircleDollarSign,
  ScanLine,
  Sparkles,
  UsersRound,
} from "lucide-react";

const steps = [
  {
    number: "01",
    title: "Snap the receipt",
    description:
      "Start with a photo or upload. Your table's order is the only thing you need.",
    icon: ScanLine,
  },
  {
    number: "02",
    title: "Say who had what",
    description:
      "Tell Splitsnap in plain English. Review every item and share before moving on.",
    icon: UsersRound,
  },
  {
    number: "03",
    title: "Settle together",
    description:
      "See a clear breakdown for everyone. Nothing gets invoiced until you approve it.",
    icon: CircleDollarSign,
  },
];

export default function Home() {
  return (
    <main className="min-h-screen overflow-hidden">
      <header className="mx-auto flex w-full max-w-7xl items-center justify-between px-5 py-5 sm:px-8 lg:px-12">
        <a
          aria-label="Splitsnap home"
          className="flex items-center gap-2.5"
          href="/"
        >
          <span className="grid size-9 place-items-center rounded-xl bg-[var(--green)] text-white">
            <ScanLine aria-hidden="true" size={19} strokeWidth={2.2} />
          </span>
          <span className="text-lg font-semibold tracking-tight">splitsnap</span>
        </a>
        <a
          className="inline-flex items-center gap-2 rounded-full border border-[var(--line)] bg-white px-4 py-2.5 text-sm font-medium transition hover:border-[var(--green)] hover:text-[var(--green)]"
          href="#how-it-works"
        >
          How it works <ArrowDown aria-hidden="true" size={15} />
        </a>
      </header>

      <section className="mx-auto grid w-full max-w-7xl items-center gap-12 px-5 pb-20 pt-12 sm:px-8 sm:pb-28 sm:pt-20 lg:grid-cols-[1.05fr_0.95fr] lg:gap-16 lg:px-12 lg:pt-24">
        <div className="relative z-10">
          <div className="mb-7 inline-flex items-center gap-2 rounded-full border border-[#dce7d7] bg-[#f0f5eb] px-3.5 py-2 text-xs font-medium text-[var(--green)]">
            <Sparkles aria-hidden="true" size={14} />
            A better way to split dinner
          </div>
          <h1 className="max-w-2xl text-5xl leading-[1.04] font-semibold tracking-[-0.055em] sm:text-6xl lg:text-[4.5rem]">
            Split the bill,
            <br />
            <span className="text-[var(--green)]">not the moment.</span>
          </h1>
          <p className="mt-6 max-w-lg text-base leading-7 text-[var(--muted)] sm:text-lg sm:leading-8">
            One receipt, a table full of people, and no awkward math. Make
            everyone&apos;s share clear before the good night ends.
          </p>
          <a
            className="mt-8 inline-flex min-h-12 items-center justify-center gap-2 rounded-full bg-[var(--green)] px-6 text-sm font-semibold text-white transition hover:bg-[var(--green-dark)] focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[var(--green)]"
            href="#how-it-works"
          >
            See how it works <ArrowRight aria-hidden="true" size={17} />
          </a>
          <div className="mt-7 flex items-center gap-2 text-sm text-[var(--muted)]">
            <Check aria-hidden="true" className="text-[var(--green)]" size={16} />
            You review every split before anything is sent
          </div>
        </div>

        <div
          aria-label="Illustration of a restaurant receipt with a reviewed bill split"
          className="relative mx-auto w-full max-w-[500px]"
          role="img"
        >
          <div className="absolute -right-6 -top-8 size-36 rounded-full bg-[#e8edda] blur-3xl sm:-right-12 sm:size-52" />
          <div className="absolute -bottom-8 -left-7 size-36 rounded-full bg-[#f2dfc9] blur-3xl sm:-left-12 sm:size-52" />
          <div className="relative rotate-[-2deg] rounded-[2rem] border border-[#e8e8e0] bg-white p-5 shadow-[0_28px_90px_-42px_rgba(35,51,39,0.3)] sm:p-8">
            <div className="flex items-start justify-between border-b border-dashed border-[var(--line)] pb-5">
              <div>
                <p className="text-xs font-medium tracking-[0.16em] text-[var(--muted)] uppercase">
                  Tonight&apos;s table
                </p>
                <h2 className="mt-1.5 text-xl font-semibold tracking-tight">
                  The Garden Room
                </h2>
              </div>
              <div className="grid size-10 place-items-center rounded-xl bg-[#f1f5ea] text-[var(--green)]">
                <ScanLine aria-hidden="true" size={20} />
              </div>
            </div>

            <div className="space-y-4 py-5">
              {[
                ["Roasted carrots", "$12.00"],
                ["Wild mushroom pasta", "$24.00"],
                ["Wood-fired sourdough", "$8.00"],
              ].map(([item, price]) => (
                <div
                  className="flex items-center justify-between text-sm"
                  key={item}
                >
                  <span className="text-[#535a52]">{item}</span>
                  <span className="font-medium tabular-nums">{price}</span>
                </div>
              ))}
            </div>

            <div className="flex items-center justify-between border-t border-[var(--line)] pt-4">
              <span className="font-medium">Table total</span>
              <span className="text-xl font-semibold tracking-tight tabular-nums">
                $44.00
              </span>
            </div>

            <div className="mt-5 rounded-2xl bg-[#f5f7f1] p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <div className="grid size-8 place-items-center rounded-full bg-[#e4edd8] text-xs font-semibold text-[var(--green)]">
                    J
                  </div>
                  <div>
                    <p className="text-sm font-semibold">Jamie&apos;s share</p>
                    <p className="text-xs text-[var(--muted)]">
                      Pasta + sourdough
                    </p>
                  </div>
                </div>
                <span className="font-semibold tabular-nums">$32.00</span>
              </div>
              <div className="mt-3 flex items-center gap-1.5 text-xs font-medium text-[var(--green)]">
                <Check aria-hidden="true" size={14} />
                Ready for your review
              </div>
            </div>
          </div>
          <div className="absolute -right-2 top-[42%] hidden -rotate-3 items-center gap-2 rounded-full border border-[#e9e9e1] bg-white px-3.5 py-2.5 text-xs font-medium shadow-lg sm:flex">
            <span className="size-2 rounded-full bg-[#7ea274]" />
            Every item accounted for
          </div>
        </div>
      </section>

      <section
        className="border-y border-[var(--line)] bg-white/70"
        id="how-it-works"
      >
        <div className="mx-auto max-w-7xl px-5 py-16 sm:px-8 sm:py-20 lg:px-12">
          <div className="max-w-xl">
            <p className="text-xs font-semibold tracking-[0.17em] text-[var(--green)] uppercase">
              Simple by design
            </p>
            <h2 className="mt-3 text-3xl font-semibold tracking-[-0.04em] sm:text-4xl">
              Back to the conversation.
            </h2>
            <p className="mt-3 leading-7 text-[var(--muted)]">
              Less time sorting out the check. More time with your people.
            </p>
          </div>
          <div className="mt-10 grid gap-4 md:grid-cols-3">
            {steps.map(({ number, title, description, icon: Icon }) => (
              <article
                className="rounded-3xl border border-[var(--line)] bg-white p-6 sm:p-7"
                key={number}
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold tracking-widest text-[#969b92]">
                    {number}
                  </span>
                  <span className="grid size-10 place-items-center rounded-xl bg-[#f1f5ea] text-[var(--green)]">
                    <Icon aria-hidden="true" size={19} />
                  </span>
                </div>
                <h3 className="mt-7 text-lg font-semibold tracking-tight">
                  {title}
                </h3>
                <p className="mt-2 text-sm leading-6 text-[var(--muted)]">
                  {description}
                </p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <footer className="mx-auto flex max-w-7xl flex-col gap-2 px-5 py-7 text-xs text-[var(--muted)] sm:flex-row sm:items-center sm:justify-between sm:px-8 lg:px-12">
        <span className="font-semibold tracking-tight text-[var(--foreground)]">
          splitsnap
        </span>
        <span>Good company. Clear shares. Your call before anything is sent.</span>
      </footer>
    </main>
  );
}
