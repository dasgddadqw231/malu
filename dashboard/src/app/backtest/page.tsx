import { connection } from "next/server";
import BacktestPageClient from "./backtest-client";

export default async function BacktestPage() {
  await connection();
  return <BacktestPageClient />;
}
