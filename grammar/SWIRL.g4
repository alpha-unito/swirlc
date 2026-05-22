grammar SWIRL;

////////////
// Parser //
////////////

// Grammar
workflow    :   location (PAR location)* EOF;
location    :   '<' name ',' dataSet ',' trace '>' ;
trace       :   trace op=(CHOICE | PAR | SEQ) trace         # TraceOp
            |   pred                                        # TracePred
            |   '(' trace ')'                               # TraceParen
            ;
pred        :   exec | send | recv;

// Functions
exec        : 'exec(' step ',' flow ',' mapping ')';
send        : 'send(' data '->' port ',' src ',' dst ')';
recv        : 'recv(' port '->' data ',' src ',' dst ')';

// Sets
dataPair    : '(' port ',' data ')';
dataSet     : '{' dataPair? (',' dataPair)* '}';
flow        : dataSet '->' dataSet;
mapping     : '{' name? (',' name)* '}';

// Variables
data        : ID | ZERO;
dst         : ID;
name        : ID;
port        : ID;
src         : ID;
step        : ID;

///////////
// Lexer //
///////////

// Operators
CHOICE      :   '+' '[' ID ']';
PAR         :   '|';
SEQ         :   '.';

// Commons
ZERO        :   '0';
ID          :   [a-zA-Z_] [a-zA-Z0-9_]*;
WS          :   [ \n\r\t] -> skip;
