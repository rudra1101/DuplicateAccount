import { Box, Link, Typography } from "@mui/material";
import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";

interface Props {
  content: string;
}

const markdownComponents: Components = {
  p: ({ children }) => (
    <Typography
      component="p"
      variant="body2"
      sx={{
        m: 0,
        mb: 1.1,
        lineHeight: 1.7,
        "&:last-child": { mb: 0 },
      }}
    >
      {children}
    </Typography>
  ),

  h1: ({ children }) => (
    <Typography
      component="h1"
      variant="subtitle1"
      sx={{ mt: 1.5, mb: 0.75, fontWeight: 700, lineHeight: 1.35 }}
    >
      {children}
    </Typography>
  ),

  h2: ({ children }) => (
    <Typography
      component="h2"
      variant="subtitle2"
      sx={{ mt: 1.35, mb: 0.7, fontWeight: 700, lineHeight: 1.35 }}
    >
      {children}
    </Typography>
  ),

  h3: ({ children }) => (
    <Typography
      component="h3"
      variant="body2"
      sx={{ mt: 1.2, mb: 0.6, fontWeight: 700, lineHeight: 1.35 }}
    >
      {children}
    </Typography>
  ),

  strong: ({ children }) => (
    <Box component="strong" sx={{ fontWeight: 700 }}>
      {children}
    </Box>
  ),

  ul: ({ children }) => (
    <Box
      component="ul"
      sx={{
        mt: 0.5,
        mb: 1.1,
        pl: 2.6,
        "& li": { mb: 0.45 },
        "& ul": { mb: 0.35 },
      }}
    >
      {children}
    </Box>
  ),

  ol: ({ children }) => (
    <Box
      component="ol"
      sx={{
        mt: 0.5,
        mb: 1.1,
        pl: 2.8,
        "& li": { mb: 0.45 },
        "& ol": { mb: 0.35 },
      }}
    >
      {children}
    </Box>
  ),

  li: ({ children }) => (
    <Box component="li" sx={{ typography: "body2", lineHeight: 1.65 }}>
      {children}
    </Box>
  ),

  blockquote: ({ children }) => (
    <Box
      component="blockquote"
      sx={{
        m: 0,
        my: 1,
        pl: 1.5,
        py: 0.25,
        borderLeft: 3,
        borderColor: "primary.main",
        color: "text.secondary",
        "& > :last-child": { mb: 0 },
      }}
    >
      {children}
    </Box>
  ),

  hr: () => (
    <Box
      component="hr"
      sx={{ my: 1.5, border: 0, borderTop: 1, borderColor: "divider" }}
    />
  ),

  a: ({ href, children }) => (
    <Link
      href={href}
      target="_blank"
      rel="noreferrer"
      underline="hover"
      sx={{ overflowWrap: "anywhere" }}
    >
      {children}
    </Link>
  ),

  pre: ({ children }) => (
    <Box
      component="pre"
      sx={{
        m: 0,
        my: 1.15,
        p: 1.35,
        maxWidth: "100%",
        overflowX: "auto",
        borderRadius: 1.5,
        border: 1,
        borderColor: "divider",
        bgcolor: "background.default",
        fontFamily: '"Cascadia Code", "JetBrains Mono", "Consolas", monospace',
        fontSize: "0.78rem",
        lineHeight: 1.55,
        whiteSpace: "pre",
      }}
    >
      {children}
    </Box>
  ),

  code: ({ className, children }) => {
    const isFencedCode = Boolean(className);

    if (isFencedCode) {
      return (
        <Box
          component="code"
          className={className}
          sx={{ display: "block", fontFamily: "inherit", fontSize: "inherit", lineHeight: "inherit" }}
        >
          {children}
        </Box>
      );
    }

    return (
      <Box
        component="code"
        sx={{
          px: 0.55,
          py: 0.15,
          borderRadius: 0.75,
          bgcolor: "action.selected",
          fontFamily: '"Cascadia Code", "JetBrains Mono", "Consolas", monospace',
          fontSize: "0.82em",
          overflowWrap: "anywhere",
        }}
      >
        {children}
      </Box>
    );
  },

  table: ({ children }) => (
    <Box
      sx={{
        width: "100%",
        my: 1.2,
        overflowX: "auto",
        border: 1,
        borderColor: "divider",
        borderRadius: 1.5,
      }}
    >
      <Box
        component="table"
        sx={{
          width: "100%",
          minWidth: 420,
          borderCollapse: "collapse",
          fontSize: "0.78rem",
          "& th, & td": {
            px: 1,
            py: 0.8,
            textAlign: "left",
            verticalAlign: "top",
            borderBottom: 1,
            borderRight: 1,
            borderColor: "divider",
            lineHeight: 1.45,
          },
          "& th": {
            bgcolor: "action.selected",
            fontWeight: 700,
            whiteSpace: "nowrap",
          },
          "& tr:last-child td": { borderBottom: 0 },
          "& th:last-child, & td:last-child": { borderRight: 0 },
        }}
      >
        {children}
      </Box>
    </Box>
  ),
};

const MarkdownMessage = ({ content }: Props) => {
  return (
    <Box
      sx={{
        minWidth: 0,
        "& > :first-of-type": { mt: 0 },
        "& > :last-child": { mb: 0 },
      }}
    >
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={markdownComponents}
      >
        {content}
      </ReactMarkdown>
    </Box>
  );
};

export default MarkdownMessage;