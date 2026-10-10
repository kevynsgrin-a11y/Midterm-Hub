export type NoteSegment = Readonly<{
  text: string;
  href?: string;
}>;

export function splitNoteLinks(text: string | null | undefined): NoteSegment[];
