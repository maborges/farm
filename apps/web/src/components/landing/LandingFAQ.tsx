"use client";

import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";

interface FaqItem {
  question: string;
  answer: string;
}

interface LandingFAQProps {
  items: FaqItem[];
}

/**
 * Seção de FAQ usando shadcn Accordion.
 * Componente client porque AccordionPrimitive exige interatividade.
 */
export function LandingFAQ({ items }: LandingFAQProps) {
  return (
    <Accordion type="single" collapsible className="w-full">
      {items.map((item, i) => (
        <AccordionItem
          key={i}
          value={`faq-${i}`}
          className="border-border/50 px-1"
        >
          <AccordionTrigger className="text-left text-base font-bold hover:text-primary hover:no-underline">
            {item.question}
          </AccordionTrigger>
          <AccordionContent className="text-muted-foreground leading-7">
            {item.answer}
          </AccordionContent>
        </AccordionItem>
      ))}
    </Accordion>
  );
}
