grammar SWIRL;

////////////
// Parser //
////////////

// Grammar
workflow    :   location (PAR location)* EOF;
location    :   '<' name ',' dataSet ',' trace '>';
trace       :   REPL trace                                  # TraceRepl
            |   trace op=(CHOICE | PAR | SEQ) trace         # TraceOp
            |   pred                                        # TracePred
            |   ZERO                                        # TraceZero
            |   '(' trace ')'                               # TraceParen
            ;

pred        :   exec | send | recv | move;

// Functions
exec        : 'exec(' step ',' flow ',' mapping ')';
send        : 'send(' data '->' port ',' src ',' dst ')';
recv        : 'recv(' data '->' port ',' src ',' dst ')';
move        : 'move(' data '->' port ',' src ',' dst ')';


// Sets
dataPair    : '(' port ',' data ')' | '(' data ',' port ')';
dataSet     : '{' dataPair? (',' dataPair)* '}';
flow        : dataSet '->' dataSet;
locationSet : '{' name? (',' name)* '}' | ID;
mapping     : locationSet;

// Variables
data        : ID | ZERO | EOF_VAL;
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
CHOICE      :   '+' ('[' ID ']')?;
PAR         :   '|';
SEQ         :   '.';

// Keywords
EOF_VAL     :   'eof';
IN          :   'in';

// Commons
ZERO        :   '0';
ID          :   [a-zA-Z_] [a-zA-Z0-9_]*;
WS          :   [ \n\r\t]+ -> skip;
COMMENT     :   '//' ~[\r\n]* -> skip;
BLOCK_COMMENT:  '/*' .*? '*/' -> skip;

