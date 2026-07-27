import { PageSkeleton } from "@/components/PageSkeleton";

/**
 * The fallback for every screen in the app.
 *
 * One file at the group level rather than eleven: the pages differ in what
 * they load, not in what waiting for it should look like. A route that wants
 * its own can still drop a `loading.tsx` beside its `page.tsx`.
 */
export default function Loading() {
  return <PageSkeleton />;
}
