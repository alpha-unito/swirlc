grammar SWIRL;

////////////
// Parser //
////////////

// Grammar
workflow    :   location (PAR location)* EOF;
location    :   '<' name ',' dataSet ',' trace '>';
trace       :   REPL trace                                  # TraceRepl
            |   trace op=SEQ trace                          # TraceOp
            |   trace op=PAR trace                          # TraceOp
            |   trace op=CHOICE guard? trace         # TraceOp
            |   pred                                        # TracePred
            |   ZERO                                        # TraceZero
            |   '(' trace ')'                               # TraceParen
            ;

pred        :   exec | send | recv | move | end;

// Functions
exec        : 'exec(' step ',' flow ',' mapping ')';
send        : 'send(' data '->' port ',' src ',' dst ')';
recv        : 'recv(' data '->' port ',' src ',' dst ')';
move        : 'move(' data '->' port ',' src ',' dst ')';


end         : 'end()';
guard       : '[' port 'has' 'data' IN data ']';

// Sets
dataPair    : '(' port ',' data ')' | '(' data ',' port ')' | collection;
collection  : 'U(' port ',' name ',' data ')';
dataSet     : '{' dataPair? (',' dataPair)* '}';
flow        : dataSet '->' dataSet;
locationSet : '{' name? (',' name)* '}' | ID;
mapping     : locationSet;

// Variables
data        : data '/' data | '?' ID | ID ('[' ID ']')? | ZERO | EOF_VAL | BEGIN_VAL | '(' data ',' data (',' data)* ')';
dst         : locationSet;
name        : ID;
port        : ID;
src         : ID;
step        : ID;


///////////
// Lexer //
///////////

// Operators
REPL        :   '!';
CHOICE      :   '+';
PAR         :   '|';
SEQ         :   '.';

// Keywords
EOF_VAL     :   'eof';
BEGIN_VAL   :   'begin';
IN          :   'in';

// Commons
ZERO        :   '0';
ID          :   [a-zA-Z_] [a-zA-Z0-9_]*;
WS          :   [ \n\r\t]+ -> skip;
COMMENT     :   '//' ~[\r\n]* -> skip;
BLOCK_COMMENT:  '/*' .*? '*/' -> skip;
