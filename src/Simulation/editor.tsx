"use strict";

import * as React from "react";
import isHotkey from 'is-hotkey'
import { Editable, withReact, Slate, useSlate } from 'slate-react';
import { createEditor, Transforms, Editor, Range } from 'slate';
import { withHistory } from 'slate-history';
import { Button } from 'react-bootstrap';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faItalic, faBold, faUnderline, faListOl, faQuoteRight, faListUl, faHeading, faLink } from '@fortawesome/free-solid-svg-icons';
import { IconDefinition } from '@fortawesome/fontawesome-svg-core'
import { isUrl } from "../utils";

type Mark = "bold" | "italic" | "underline" | "strikethrough";
type Block = "heading-one" | "heading-two" | "block-quote" | "numbered-list" | "bulleted-list" | "link";


interface SlateValue {
  type: string;
  children: { text: string }[];
}

const HOTKEYS = {
  'mod+b': 'bold',
  'mod+i': 'italic',
  'mod+u': 'underline',
  'mod+`': 'code',
  // 'mod+k': 'link', TODO
}

const LIST_TYPES = ['numbered-list', 'bulleted-list']

const ReadmeEditor: React.FC<{
  fieldName: string;
  value: SlateValue[];
  setFieldValue: (field: string, value: any) => void,
  handleSubmit: (e?: any) => void,
  readOnly: boolean,
}> = ({ fieldName, value, setFieldValue, handleSubmit, readOnly }) => {
  const renderElement = React.useCallback(props => <Element {...props} />, [])
  const renderLeaf = React.useCallback(props => <Leaf {...props} />, [])
  const editor = React.useMemo(
    () => withLinks(withHistory(withReact(createEditor()))),
    []
  )
  return (
    <Slate
      editor={editor}
      value={value}
      onChange={(value: SlateValue[]) => {
        // setValue(value);
        setFieldValue(fieldName, value);
        setTimeout(handleSubmit, 0);
      }}>
      {readOnly ? null :
        <div className="mb-3">
          <MarkButton mark="bold" icon={faBold} />
          <MarkButton mark="italic" icon={faItalic} />
          <MarkButton mark="underline" icon={faUnderline} />
          <LinkButton icon={faLink} />
          <BlockButton block="heading-one" icon={faHeading} />
          <BlockButton block="block-quote" icon={faQuoteRight} />
          <BlockButton block="numbered-list" icon={faListOl} />
          <BlockButton block="bulleted-list" icon={faListUl} />
        </div>}
      <Editable
        readOnly={readOnly}
        renderElement={renderElement}
        renderLeaf={renderLeaf}
        onKeyDown={event => {
          for (const hotkey in HOTKEYS) {
            if (isHotkey(hotkey, event)) {
              event.preventDefault();
              const mark = HOTKEYS[hotkey];
              Controller.toggleMark(editor, mark);
            }
          }
        }
        }
      />
    </Slate >
  )
}


const withLinks = editor => {
  const { insertData, insertText, isInline } = editor;

  editor.isInline = element => {
    return element.type === 'link' ? true : isInline(element);
  }

  editor.insertText = text => {
    if (text && isUrl(text)) {
      Controller.wrapLink(editor, text);
    } else {
      insertText(text);
    }
  }

  editor.insertData = data => {
    const text = data.getData('text/plain');

    if (text && isUrl(text)) {
      Controller.wrapLink(editor, text);
    } else {
      insertData(data);
    }
  }

  return editor;
}

const Element = ({ attributes, children, element }) => {
  switch (element.type) {
    case 'block-quote':
      return <blockquote className="blockquote" {...attributes}>{children}</blockquote>
    case 'bulleted-list':
      return <ul {...attributes}>{children}</ul>
    case 'heading-one':
      return <h5 {...attributes}>{children}</h5>
    case 'list-item':
      return <li {...attributes}>{children}</li>
    case 'numbered-list':
      return <ol {...attributes}>{children}</ol>
    case 'link':
      return (
        <a {...attributes} href={element.url}>
          {children}
        </a>
      );
    default:
      return <p {...attributes}>{children}</p>
  }
}
const Leaf = ({ attributes, children, leaf }) => {
  if (leaf.bold) {
    children = <strong>{children}</strong>
  }

  if (leaf.italic) {
    children = <em>{children}</em>
  }

  if (leaf.underline) {
    children = <u>{children}</u>
  }

  return <span {...attributes}>{children}</span>
}

const BlockButton: React.FC<{ block: Block, icon: IconDefinition }> = ({ block, icon }) => {
  const editor = useSlate();
  const active = Controller.isBlockActive(editor, block);
  return (
    <Button
      size="sm"
      variant={Controller.isBlockActive(editor, block) ? "dark" : "light"}
      style={{ border: 0, backgroundColor: active ? "rgba(60, 62, 62, 1)" : "white" }}
      onMouseDown={event => {
        event.preventDefault();
        Controller.toggleBlock(editor, block);
      }}
    >
      <FontAwesomeIcon icon={icon} />
    </Button >
  )
}

const MarkButton: React.FC<{ mark: Mark, icon: IconDefinition }> = ({ mark, icon }) => {
  const editor = useSlate();
  const active = Controller.isMarkActive(editor, mark);
  return (
    <Button
      size="sm"
      variant={active ? "dark" : "light"}
      style={{ border: 0, backgroundColor: active ? "rgba(60, 62, 62, 1)" : "white" }}
      onMouseDown={event => {
        event.preventDefault();
        Controller.toggleMark(editor, mark);
      }}
    >
      <FontAwesomeIcon icon={icon} />
    </Button>
  )
}

const LinkButton: React.FC<{ icon: IconDefinition }> = ({ icon }) => {
  const editor = useSlate();
  const active = Controller.isBlockActive(editor, "link");
  return (
    <Button
      size="sm"
      variant={active ? "dark" : "light"}
      style={{ border: 0, backgroundColor: active ? "rgba(60, 62, 62, 1)" : "white" }}
      onMouseDown={event => {
        event.preventDefault()
        const url = window.prompt('Enter the URL of the link:')
        if (!url) return
        Controller.insertLink(editor, url);
      }}
    >
      <FontAwesomeIcon icon={icon} />
    </Button>
  )
}

const Controller = {
  isMarkActive(editor: Editor, mark: Mark) {
    const marks = Editor.marks(editor);
    return marks ? marks[mark] === true : false;
  },

  isBlockActive(editor: Editor, block: Block) {
    const [match] = Editor.nodes(editor, {
      match: n => n.type === block,
    });

    return !!match
  },

  toggleMark(editor: Editor, mark: Mark) {
    const isActive = Controller.isMarkActive(editor, mark)

    if (isActive) {
      Editor.removeMark(editor, mark)
    } else {
      Editor.addMark(editor, mark, true)
    }
  },

  toggleBlock(editor: Editor, block: Block) {
    const isActive = Controller.isBlockActive(editor, block);
    const isList = LIST_TYPES.includes(block);

    Transforms.unwrapNodes(editor, {
      match: n => LIST_TYPES.includes(n.type),
      split: true,
    });

    Transforms.setNodes(editor, {
      type: isActive ? 'paragraph' : isList ? 'list-item' : block,
    });

    if (!isActive && isList) {
      const el = { type: block, children: [] };
      Transforms.wrapNodes(editor, el);
    }
  },

  insertLink(editor: Editor, url: string | URL) {
    if (editor.selection) {
      Controller.wrapLink(editor, url);
    }
  },

  unwrapLink(editor: Editor) {
    Transforms.unwrapNodes(editor, { match: n => n.type === 'link' });
  },

  wrapLink(editor, url) {
    if (Controller.isBlockActive(editor, "link")) {
      Controller.unwrapLink(editor);
    }

    const { selection } = editor
    const isCollapsed = selection && Range.isCollapsed(selection);
    const link = {
      type: 'link',
      url,
      children: isCollapsed ? [{ text: url }] : [],
    }

    if (isCollapsed) {
      Transforms.insertNodes(editor, link);
    } else {
      Transforms.wrapNodes(editor, link, { split: true });
      Transforms.collapse(editor, { edge: 'end' });
    }
  }
}


export default ReadmeEditor;