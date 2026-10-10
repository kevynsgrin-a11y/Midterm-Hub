import { Fragment } from "react";
import { splitNoteLinks } from "@/lib/note-links.mjs";
/** Record notes are plain text; a bare http(s) URL in one renders as an external link. */
export function NoteText({text}:{text?:string|null}){return <>{splitNoteLinks(text).map((part,i)=>part.href?<a key={i} href={part.href} target="_blank" rel="noreferrer" className="editorial-link">{part.text}</a>:<Fragment key={i}>{part.text}</Fragment>)}</>}
