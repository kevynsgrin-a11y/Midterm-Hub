import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";
const variants = cva("inline-flex min-h-11 items-center justify-center gap-2 rounded-sm border px-4 py-2 text-sm font-bold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50",{variants:{variant:{default:"border-primary bg-primary text-primary-foreground hover:bg-primary/90",outline:"border-border bg-background text-foreground hover:bg-muted",ghost:"border-transparent text-foreground hover:bg-muted"},size:{default:"h-11",sm:"h-9 min-h-9 px-3"}},defaultVariants:{variant:"default",size:"default"}});
export function Button({className,variant,size,asChild=false,...props}:React.ComponentProps<"button">&VariantProps<typeof variants>&{asChild?:boolean}){const Comp=asChild?Slot:"button";return <Comp className={cn(variants({variant,size}),className)} {...props}/>}
