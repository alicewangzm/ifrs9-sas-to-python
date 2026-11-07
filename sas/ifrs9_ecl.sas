/*=====================================================================
  IFRS 9 Expected Credit Loss (simplified) - legacy SAS version
  ---------------------------------------------------------------------
  Input : loans.csv
  Output: sas_ecl_loan_level.csv, sas_ecl_summary.csv

  Steps
    1. Read the loan file
    2. Fill missing current PD with a segment default
    3. Exposure at default (EAD) = balance + CCF * undrawn limit
    4. Remaining term in months (INTCK) and lifetime PD
    5. Stage: 3 = 90+ days past due, 2 = 30+ DPD or PD at least doubled
              since origination (SICR), 1 = everything else
    6. ECL = PD (12-month for Stage 1, lifetime for Stage 2, 1 for
             Stage 3) x LGD x EAD
    7. Summary by segment and stage

  Simplified for a demo: no discounting, no forward-looking scenarios.

  SAS OnDemand for Academics: upload loans.csv into a folder called
  ifrs9 in your home directory, or change PATH below to wherever
  you put it (right-click the folder > Properties shows the path).
=====================================================================*/

%let path     = ~/ifrs9;
%let rpt_date = '31OCT2026'd;

/* 1. Read input --------------------------------------------------- */
data work.loans;
  infile "&path/loans.csv" dsd firstobs=2 truncover;
  length loan_id $10 segment $10;
  input loan_id $ segment $
        origination_date :yymmdd10. maturity_date :yymmdd10.
        balance undrawn_limit ccf pd_orig pd_curr lgd days_past_due;
  format origination_date maturity_date yymmdd10.;
run;

/* 2-6. Loan-level ECL --------------------------------------------- */
data work.ecl_loan_level;
  set work.loans;
  length pd_source $7;

  /* 2. Missing current PD -> segment default */
  if missing(pd_curr) then do;
    select (segment);
      when ('MORTGAGE') pd_curr = 0.004;
      when ('AUTO')     pd_curr = 0.015;
      when ('CARD')     pd_curr = 0.030;
      when ('SME')      pd_curr = 0.025;
      otherwise         pd_curr = 0.050;
    end;
    pd_source = 'DEFAULT';
  end;
  else pd_source = 'MODEL';

  /* 3. Exposure at default */
  ead = round(balance + ccf * undrawn_limit, 0.01);

  /* 4. Remaining term and lifetime PD.
        INTCK counts month boundaries crossed, not elapsed months. */
  term_months = intck('month', &rpt_date, maturity_date);
  if term_months < 1 then term_months = 1;
  pd_lifetime = 1 - (1 - pd_curr) ** (term_months / 12);

  /* 5. Staging.
        Note: if pd_orig is missing, 2 * pd_orig is missing, and in SAS
        any number >= missing is TRUE, so those loans land in Stage 2. */
  if days_past_due >= 90 then stage = 3;
  else if days_past_due >= 30 or pd_curr >= 2 * pd_orig then stage = 2;
  else stage = 1;

  /* 6. ECL */
  select (stage);
    when (1) pd_used = pd_curr;
    when (2) pd_used = pd_lifetime;
    when (3) pd_used = 1;
  end;
  ecl = round(pd_used * lgd * ead, 0.01);

  format ead ecl 15.2 pd_curr pd_lifetime pd_used 12.10 lgd 8.4;
  keep loan_id segment stage pd_source term_months ead
       pd_curr pd_lifetime pd_used lgd ecl;
run;

/* 7. Summary ------------------------------------------------------ */
proc sql;
  create table work.ecl_summary as
  select segment,
         stage,
         count(*)                                    as n_loans,
         sum(ead)                                    as total_ead format=18.2,
         sum(ecl)                                    as total_ecl format=18.2,
         calculated total_ecl / calculated total_ead as coverage  format=12.8
  from work.ecl_loan_level
  group by segment, stage
  order by segment, stage;
quit;

proc print data=work.ecl_summary noobs; title 'ECL by segment and stage (SAS)'; run;

/* Export for the parallel run ------------------------------------ */
proc export data=work.ecl_loan_level outfile="&path/sas_ecl_loan_level.csv"
            dbms=csv replace;
run;

proc export data=work.ecl_summary outfile="&path/sas_ecl_summary.csv"
            dbms=csv replace;
run;
